"""Tests for ChatGPT auto-fix orchestration and LOW-risk remediation executor."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock

import pytest

from src.network_recovery.auto_fix import run_auto_fix_chatgpt
from src.network_recovery.models import SignalBundle
from src.network_recovery.remediation_catalog import remediation_previews_for_chatgpt_scenario
from src.network_recovery.remediation_executor import (
    CONFIRMATION_PHRASE,
    execute_selected_low_risk_actions,
    select_low_risk_actions,
    validate_chatgpt_remediation_confirmation,
)
from src.network_recovery.scenarios.chatgpt_app_firewall import analyze_chatgpt_app_firewall


def _degraded_signals(**overrides: object) -> SignalBundle:
    base = dict(
        browser_https_ok=True,
        chatgpt_https_ok=False,
        openai_https_ok=False,
        curl_https_ok=True,
        dns_ok=True,
        wininet_proxy_enable=0,
        wininet_proxy_server=None,
        wininet_auto_config_url=None,
        winhttp_direct_access=True,
        winhttp_loopback_hint=False,
        firewall_profiles_snapshot={},
        localhost_listener_ports=(),
        chatgpt_process_detected=True,
        electron_process_detected=True,
        vpn_adapter_hint=False,
        collector_notes=(),
    )
    base.update(overrides)
    return SignalBundle(**base)  # type: ignore[arg-type]


def test_confirmation_gate_blocks_live_without_token() -> None:
    ok, reason = validate_chatgpt_remediation_confirmation(dry_run=False, confirm="")
    assert ok is False
    assert CONFIRMATION_PHRASE in reason


def test_confirmation_gate_allows_dry_run() -> None:
    ok, _ = validate_chatgpt_remediation_confirmation(dry_run=True, confirm="")
    assert ok is True


def test_select_low_risk_actions_for_dns_failure() -> None:
    signals = _degraded_signals(dns_ok=False)
    analysis = analyze_chatgpt_app_firewall(signals)
    selected = select_low_risk_actions(signals, analysis["hypotheses"])  # type: ignore[arg-type]
    assert "flush_dns" in selected


def test_high_process_fanout_and_state_select_reversible_cold_restart() -> None:
    signals = _degraded_signals(
        chatgpt_process_count=99,
        chatgpt_network_state_file_count=1,
        chatgpt_network_state_locations=(r"%APPDATA%\ChatGPT\Network\Network Persistent State",),
    )
    analysis = analyze_chatgpt_app_firewall(signals)
    selected = select_low_risk_actions(signals, analysis["hypotheses"])  # type: ignore[arg-type]
    cache = next(
        h
        for h in analysis["hypotheses"]
        if h.hypothesis_id == "app_cache_or_session_issue"  # type: ignore[union-attr]
    )

    assert cache.confidence == "medium"
    assert any("99" in row and "not proof" in row for row in cache.evidence_for)
    assert "cold_restart_chatgpt_network_state" in selected
    assert "restart_chatgpt_app" not in selected


def test_select_low_risk_actions_skips_when_healthy() -> None:
    signals = _degraded_signals(chatgpt_https_ok=True, openai_https_ok=True)
    analysis = analyze_chatgpt_app_firewall(signals)
    selected = select_low_risk_actions(signals, analysis["hypotheses"])  # type: ignore[arg-type]
    assert selected == []


def test_execute_low_risk_dry_run_never_calls_subprocess() -> None:
    run = MagicMock()
    previews = remediation_previews_for_chatgpt_scenario(dry_run=False)
    blob = execute_selected_low_risk_actions(
        ["flush_dns", "disable_firewall"],
        dry_run=True,
        confirm="",
        previews=previews,
        run=run,
    )
    run.assert_not_called()
    assert blob["executed"] == ["flush_dns"]
    blocked = next(r for r in blob["results"] if r["action_id"] == "disable_firewall")
    assert blocked["policy_decision"] == "BLOCK"


def test_execute_low_risk_live_requires_confirm() -> None:
    run = MagicMock()
    blob = execute_selected_low_risk_actions(
        ["flush_dns"],
        dry_run=False,
        confirm="",
        run=run,
    )
    assert blob["executed"] == []
    assert run.call_count == 0


def test_execute_low_risk_live_with_confirm() -> None:
    proc = MagicMock(returncode=0, stdout="ok", stderr="")
    run = MagicMock(return_value=proc)
    blob = execute_selected_low_risk_actions(
        ["flush_dns"],
        dry_run=False,
        confirm=CONFIRMATION_PHRASE,
        run=run,
    )
    assert blob["executed"] == ["flush_dns"]
    run.assert_called_once()


def test_auto_fix_default_is_preview_only() -> None:
    assert inspect.signature(run_auto_fix_chatgpt).parameters["dry_run"].default is True


def test_app_apply_does_not_auto_confirm_proxy_guardian(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guardian_dry_runs: list[bool] = []
    healthy = _degraded_signals(chatgpt_https_ok=True, openai_https_ok=True)
    diagnosis = __import__(
        "src.network_recovery.engine", fromlist=["run_scenario_diagnosis"]
    ).run_scenario_diagnosis(
        "chatgpt_app_firewall",
        signals=healthy,
        collect_live=False,
        dry_run=False,
    )
    monkeypatch.setattr("src.network_recovery.auto_fix.platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_proxy_guardian_once",
        lambda *, dry_run: (
            guardian_dry_runs.append(dry_run)
            or {"action_taken": "preview_only" if dry_run else "remediated"}
        ),
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_proxy_status",
        lambda: {"classification": "NO_PROXY"},
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_bad_gateway_diagnose",
        lambda *_a, **_k: {"headline": "fixture"},
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_scenario_diagnosis",
        lambda *_a, **_k: diagnosis,
    )

    run_auto_fix_chatgpt(
        dry_run=False,
        confirm=CONFIRMATION_PHRASE,
        proxy_confirm="",
        repo_root=tmp_path,
    )
    run_auto_fix_chatgpt(
        dry_run=False,
        confirm=CONFIRMATION_PHRASE,
        proxy_confirm="CLEAR_DEAD_LOCALHOST_PROXY",
        repo_root=tmp_path,
    )

    assert guardian_dry_runs == [True, False]


def test_cold_restart_live_requires_token_and_preserves_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roaming = tmp_path / "Roaming"
    local = tmp_path / "Local"
    state = roaming / "ChatGPT" / "Network" / "Network Persistent State"
    state.parent.mkdir(parents=True)
    state.write_text("fixture", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    run = MagicMock()

    blob = execute_selected_low_risk_actions(
        ["cold_restart_chatgpt_network_state"],
        dry_run=False,
        confirm="",
        run=run,
    )

    assert blob["executed"] == []
    assert state.read_text(encoding="utf-8") == "fixture"
    run.assert_not_called()


def test_cold_restart_dry_run_never_stops_process_or_moves_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roaming = tmp_path / "Roaming"
    state = roaming / "ChatGPT" / "Network" / "Network Persistent State"
    state.parent.mkdir(parents=True)
    state.write_text("fixture", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    run = MagicMock()

    blob = execute_selected_low_risk_actions(
        ["cold_restart_chatgpt_network_state"],
        dry_run=True,
        confirm=CONFIRMATION_PHRASE,
        run=run,
    )

    assert blob["results"][0]["executed"] is False
    assert blob["results"][0]["planned_quarantine_count"] == 1
    assert state.read_text(encoding="utf-8") == "fixture"
    run.assert_not_called()


def test_cold_restart_leaves_state_unchanged_when_exit_cannot_be_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roaming = tmp_path / "Roaming"
    state = roaming / "ChatGPT" / "Network" / "Network Persistent State"
    state.parent.mkdir(parents=True)
    state.write_text("fixture", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))

    def _run(argv: list[str], **_kwargs: object) -> CompletedProcess[str]:
        if argv[0].lower() == "tasklist":
            return CompletedProcess(argv, 1, "", "tasklist unavailable")
        return CompletedProcess(argv, 0, "", "")

    blob = execute_selected_low_risk_actions(
        ["cold_restart_chatgpt_network_state"],
        dry_run=False,
        confirm=CONFIRMATION_PHRASE,
        run=_run,
    )

    assert blob["executed"] == []
    assert blob["results"][0]["ok"] is False
    assert blob["results"][0]["quarantine"] == []
    assert state.read_text(encoding="utf-8") == "fixture"


def test_confirmed_cold_restart_quarantines_only_network_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roaming = tmp_path / "Roaming"
    local = tmp_path / "Local"
    state = roaming / "ChatGPT" / "Network" / "Network Persistent State"
    state.parent.mkdir(parents=True)
    state.write_text("fixture", encoding="utf-8")
    exe = local / "Programs" / "ChatGPT" / "ChatGPT.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fixture executable")
    session = roaming / "ChatGPT" / "Cookies"
    session.write_text("must remain", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    def _run(argv: list[str], **_kwargs: object) -> CompletedProcess[str]:
        if argv[0].lower() == "tasklist":
            return CompletedProcess(
                argv, 0, "INFO: No tasks are running which match the specified criteria.", ""
            )
        return CompletedProcess(argv, 0, "", "")

    blob = execute_selected_low_risk_actions(
        ["cold_restart_chatgpt_network_state"],
        dry_run=False,
        confirm=CONFIRMATION_PHRASE,
        run=_run,
    )

    assert blob["executed"] == ["cold_restart_chatgpt_network_state"]
    result = blob["results"][0]
    assert result["ok"] is True
    assert result["remaining_process_count"] == 0
    assert result["quarantine"][0]["status"] == "quarantined"
    assert not state.exists()
    assert list(state.parent.glob("Network Persistent State.wnrt-backup-*"))
    assert session.read_text(encoding="utf-8") == "must remain"


def test_confirmed_cold_restart_uses_bounded_force_fallback_for_remaining_chatgpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roaming = tmp_path / "Roaming"
    local = tmp_path / "Local"
    state = roaming / "ChatGPT" / "Network" / "Network Persistent State"
    state.parent.mkdir(parents=True)
    state.write_text("fixture", encoding="utf-8")
    exe = local / "Programs" / "ChatGPT" / "ChatGPT.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fixture executable")
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    tasklist_calls = 0
    powershell_commands: list[str] = []

    def _run(argv: list[str], **_kwargs: object) -> CompletedProcess[str]:
        nonlocal tasklist_calls
        if argv[0].lower() == "tasklist":
            tasklist_calls += 1
            stdout = '"ChatGPT.exe","42","Console","1","10,000 K"' if tasklist_calls == 1 else ""
            return CompletedProcess(argv, 0, stdout, "")
        if argv[0].lower() == "powershell":
            powershell_commands.append(argv[-1])
        return CompletedProcess(argv, 0, "", "")

    blob = execute_selected_low_risk_actions(
        ["cold_restart_chatgpt_network_state"],
        dry_run=False,
        confirm=CONFIRMATION_PHRASE,
        run=_run,
    )

    assert blob["executed"] == ["cold_restart_chatgpt_network_state"]
    assert tasklist_calls == 2
    assert any("-Force" in command for command in powershell_commands)
    assert blob["results"][0]["force_stop"]["returncode"] == 0


@pytest.mark.skipif(
    __import__("platform").system() != "Windows", reason="Windows-only orchestrator"
)
def test_auto_fix_chatgpt_dry_run_writes_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_proxy_guardian_once",
        lambda **_: {"action_taken": "none", "classification": "NO_PROXY"},
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_proxy_status",
        lambda **_: {"classification": "NO_PROXY"},
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_bad_gateway_diagnose",
        lambda url, dry_run=True: {"headline": "ok", "url": url},
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.run_scenario_diagnosis",
        lambda *a, **k: __import__(
            "src.network_recovery.engine", fromlist=["run_scenario_diagnosis"]
        ).run_scenario_diagnosis(
            "chatgpt_app_firewall",
            signals=_degraded_signals(),
            collect_live=False,
            dry_run=True,
        ),
    )
    monkeypatch.setattr(
        "src.network_recovery.auto_fix.collect_signals",
        lambda **_: _degraded_signals(chatgpt_https_ok=True),
    )

    payload = run_auto_fix_chatgpt(dry_run=True, repo_root=tmp_path, skip_proxy_auto_fix=False)
    assert payload["dry_run"] is True
    assert payload["diagnosis_run_id"]
    report = tmp_path / "reports" / "last_network_recovery_diagnosis.json"
    assert report.is_file()
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert blob["scenario_id"] == "chatgpt_app_firewall"

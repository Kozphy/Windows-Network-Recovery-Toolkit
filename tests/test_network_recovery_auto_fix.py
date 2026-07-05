"""Tests for ChatGPT auto-fix orchestration and LOW-risk remediation executor."""

from __future__ import annotations

import json
from pathlib import Path
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


@pytest.mark.skipif(__import__("platform").system() != "Windows", reason="Windows-only orchestrator")
def test_auto_fix_chatgpt_dry_run_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

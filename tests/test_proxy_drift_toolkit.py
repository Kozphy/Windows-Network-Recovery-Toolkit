"""Tests for targeted proxy drift detection (``src.proxy_drift``)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.proxy_drift.classify import classify_proxy_drift
from src.proxy_drift.guardian import CONFIRM_CLEAR_DEAD, run_dead_proxy_guardian_once
from src.proxy_drift.proxy_fix import build_proxy_fix_mutations
from src.proxy_drift.safe_search import _should_exclude_dir, safe_search
from src.proxy_drift.startup_inventory import collect_startup_inventory
from src.proxy_guard.parser import parse_proxy_server


def test_parse_proxy_server_localhost_port() -> None:
    parsed = parse_proxy_server("127.0.0.1:60505")
    assert parsed.is_localhost_proxy is True
    assert parsed.localhost_port == 60505


def test_classify_stale_localhost_proxy() -> None:
    out = classify_proxy_drift(
        proxy_enable=1,
        proxy_server="127.0.0.1:62285",
        listener_found=False,
    )
    assert out["classification"] == "STALE_LOCALHOST_PROXY"


def test_classify_active_localhost_proxy() -> None:
    out = classify_proxy_drift(
        proxy_enable=1,
        proxy_server="127.0.0.1:8080",
        listener_found=True,
        process_name="node.exe",
    )
    assert out["classification"] == "KNOWN_DEV_PROXY"


def test_proxy_fix_does_not_clear_corporate_proxy_server() -> None:
    mutations, lines = build_proxy_fix_mutations(proxy_server="proxy.corp.example.com:8080", clear_pac=False)
    human = "\n".join(lines)
    assert "ProxyEnable" in human
    assert "corporate proxy preserved" in human
    assert not any("ProxyServer" in m.human and "delete" in m.human.lower() for m in mutations)


def test_proxy_fix_does_not_clear_pac_by_default() -> None:
    mutations, _lines = build_proxy_fix_mutations(proxy_server="127.0.0.1:60505", clear_pac=False)
    assert not any("AutoConfigURL" in m.human for m in mutations)


def test_proxy_fix_clears_localhost_server_when_requested() -> None:
    mutations, lines = build_proxy_fix_mutations(proxy_server="127.0.0.1:60505", clear_pac=False)
    assert any("ProxyServer" in line for line in lines)
    assert len(mutations) >= 2


def test_startup_inventory_does_not_walk_full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Path] = []

    def fake_startup_folder_entries(path: Path, source: str, run: object) -> list[dict]:
        calls.append(path)
        return []

    def fake_registry(*_a: object, **_k: object) -> list[dict]:
        return []

    def fake_tasks(run: object) -> list[dict]:
        return []

    def fake_wmi(run: object) -> list[dict]:
        return []

    monkeypatch.setattr(
        "src.proxy_drift.startup_inventory._startup_folder_entries",
        fake_startup_folder_entries,
    )
    monkeypatch.setattr("src.proxy_drift.startup_inventory._registry_run_entries", fake_registry)
    monkeypatch.setattr("src.proxy_drift.startup_inventory._scheduled_task_entries", fake_tasks)
    monkeypatch.setattr("src.proxy_drift.startup_inventory._wmi_startup_entries", fake_wmi)
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    monkeypatch.setenv("ProgramData", r"C:\ProgramData")

    collect_startup_inventory(audit_path=None)

    assert calls
    assert all("Startup" in str(p) for p in calls)
    assert not any("Users\\test" == p.name for p in calls)


def test_safe_search_respects_excluded_directories() -> None:
    assert _should_exclude_dir(
        Path(r"C:\Users\x\AppData\Local\Temp\sub"),
        profile_scan=True,
    )
    assert _should_exclude_dir(Path(r"C:\proj\node_modules\pkg"))
    assert not _should_exclude_dir(Path(r"C:\proj\scripts"))


def test_safe_search_timeout_cap(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for i in range(50):
        (scripts / f"file_{i}.txt").write_text("WNRT-DeadProxyGuardian", encoding="utf-8")
    result = safe_search(
        query="WNRT-DeadProxyGuardian",
        target="scripts",
        repo_root=tmp_path,
        max_seconds=5.0,
        max_files=10,
    )
    assert result["scanned_files"] <= 11
    assert result["timed_out"] is True


def test_guardian_requires_confirmation_before_modify() -> None:
    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:60505", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=False),
        patch("src.proxy_drift.guardian.apply_proxy_fix") as fix,
    ):
        out = run_dead_proxy_guardian_once(dry_run=False, confirm="")
    fix.assert_not_called()
    assert out["action_taken"] == "blocked"


def test_guardian_applies_with_confirmation() -> None:
    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:60505", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=False),
        patch(
            "src.proxy_drift.guardian.apply_proxy_fix",
            return_value={"action_allowed": True},
        ) as fix,
    ):
        out = run_dead_proxy_guardian_once(dry_run=False, confirm=CONFIRM_CLEAR_DEAD)
    fix.assert_called_once()
    assert out["action_taken"] == "remediated"


def test_auto_fix_proxy_dry_run_skips_mutations() -> None:
    from src.proxy_drift.auto_fix import run_auto_fix_proxy

    with (
        patch("src.proxy_drift.auto_fix.run_dead_proxy_guardian_once") as guardian,
        patch("src.proxy_drift.auto_fix.apply_proxy_fix") as fix,
        patch("src.proxy_drift.auto_fix.read_proxy_drift_status") as status,
    ):
        status.return_value = {
            "classification": "NO_PROXY",
            "legacy_classification": "NO_PROXY",
            "is_dead_localhost_proxy": False,
        }
        out = run_auto_fix_proxy(dry_run=True, skip_cursor_fix=True)
    guardian.assert_called_once()
    fix.assert_not_called()
    assert out["outcome"] in {"healthy", "review", "would_remediate"}


def test_auto_fix_proxy_fallback_when_still_dead() -> None:
    from src.proxy_drift.auto_fix import run_auto_fix_proxy

    dead = {
        "classification": "STALE_LOCALHOST_PROXY",
        "legacy_classification": "DEAD_PROXY_CONFIG",
        "is_dead_localhost_proxy": True,
    }
    healthy = {
        "classification": "NO_PROXY",
        "legacy_classification": "NO_PROXY",
        "is_dead_localhost_proxy": False,
    }
    with (
        patch("src.proxy_drift.auto_fix.run_dead_proxy_guardian_once", return_value={"action_taken": "preview_only"}),
        patch("src.proxy_drift.auto_fix.apply_proxy_fix", return_value={"action_allowed": True}) as fix,
        patch(
            "src.proxy_drift.auto_fix.read_proxy_drift_status",
            side_effect=[dead, dead, healthy],
        ),
        patch("src.proxy_drift.auto_fix._install_guardian_loop", return_value={"step": "guardian_install"}),
    ):
        out = run_auto_fix_proxy(dry_run=False, skip_cursor_fix=True, skip_guardian_install=True)
    fix.assert_called_once()
    assert out["outcome"] == "healthy"


def test_classify_preserves_non_localhost_proxy() -> None:
    out = classify_proxy_drift(
        proxy_enable=1,
        proxy_server="proxy.corp.example.com:8080",
        listener_found=None,
    )
    assert out["classification"] == "INSUFFICIENT_EVIDENCE"


def test_boot_trace_snapshot_uses_proxy_actor_image_path() -> None:
    from src.proxy_drift.boot_trace import _snapshot
    from src.proxy_guard.attribution_model import LayeredAttributionResult, ProxyActor

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:60505", auto_config_url=None, proxy_override=None)
    actor = ProxyActor(
        pid=1234,
        process_name="node.exe",
        image_path=r"C:\Program Files\node.exe",
        command_line="node proxy.js",
        parent_pid=999,
        parent_process_name="Cursor.exe",
    )
    attr = LayeredAttributionResult(
        candidate_actor=actor,
        attribution_confidence="medium",
        attribution_method="localhost_listener",
    )
    with (
        patch("src.proxy_drift.boot_trace.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.boot_trace._port_listening", return_value=True),
        patch("src.proxy_drift.boot_trace.attribute_localhost_proxy_listener", return_value=attr),
        patch("src.proxy_drift.boot_trace._winhttp_direct", return_value=True),
    ):
        snap = _snapshot(MagicMock())
    assert snap["listener"]["exe_path"] == r"C:\Program Files\node.exe"
    assert snap["listener"]["process_name"] == "node.exe"

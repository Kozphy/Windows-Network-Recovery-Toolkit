"""Tests for targeted proxy drift detection (``src.proxy_drift``)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.proxy_drift.boot_trace_task import (
    CONFIRM_INSTALL as BOOT_TRACE_CONFIRM_INSTALL,
)
from src.proxy_drift.boot_trace_task import (
    build_boot_trace_task_command,
    install_boot_trace_task,
    preview_install_boot_trace_task,
    uninstall_boot_trace_task,
)
from src.proxy_drift.classify import classify_proxy_drift
from src.proxy_drift.guardian import CONFIRM_CLEAR_DEAD, run_dead_proxy_guardian_once
from src.proxy_drift.proxy_fix import build_proxy_fix_mutations
from src.proxy_drift.safe_search import _should_exclude_dir, safe_search
from src.proxy_drift.startup_inventory import collect_startup_inventory
from src.proxy_drift.startup_observability_report import summarize_boot_trace
from src.proxy_guard.parser import parse_proxy_server

# Windows-only surfaces: simulate the platform guard so Linux CI keeps this coverage.
pytestmark = pytest.mark.usefixtures("simulated_windows")


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


def test_classify_broken_localhost_proxy_listener_up_path_fail() -> None:
    out = classify_proxy_drift(
        proxy_enable=1,
        proxy_server="127.0.0.1:57150",
        listener_found=True,
        process_name="node.exe",
        proxy_probe_ok=False,
        direct_probe_ok=True,
    )
    assert out["classification"] == "BROKEN_LOCALHOST_PROXY"
    assert "prefer-direct" in out["rationale"].lower() or "broken" in out["rationale"].lower()


def test_classify_listener_up_inconclusive_when_both_probes_fail() -> None:
    out = classify_proxy_drift(
        proxy_enable=1,
        proxy_server="127.0.0.1:57150",
        listener_found=True,
        process_name="node.exe",
        proxy_probe_ok=False,
        direct_probe_ok=False,
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


def test_guardian_broken_requires_prefer_direct_confirm() -> None:
    from src.proxy_drift.guardian import CONFIRM_CLEAR_BROKEN

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:52133", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=True),
        patch("src.proxy_drift.guardian.apply_proxy_fix") as fix,
    ):
        out = run_dead_proxy_guardian_once(
            dry_run=False,
            confirm=CONFIRM_CLEAR_DEAD,
            clear_broken=True,
            confirm_broken="",
            path_health={"proxy_probe_ok": False, "direct_probe_ok": True, "proxy_status": "DIRECT_ONLY_WORKS"},
        )
    fix.assert_not_called()
    assert out["broken_localhost_proxy"] is True
    assert out["action_taken"] == "blocked"
    assert CONFIRM_CLEAR_BROKEN in out["reason"]


def test_guardian_broken_clears_with_prefer_direct_token() -> None:
    from src.proxy_drift.guardian import CONFIRM_CLEAR_BROKEN

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:52133", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=True),
        patch(
            "src.proxy_drift.guardian.apply_proxy_fix",
            return_value={"action_allowed": True},
        ) as fix,
    ):
        out = run_dead_proxy_guardian_once(
            dry_run=False,
            confirm="",
            clear_broken=True,
            confirm_broken=CONFIRM_CLEAR_BROKEN,
            path_health={"proxy_probe_ok": False, "direct_probe_ok": True, "proxy_status": "DIRECT_ONLY_WORKS"},
        )
    fix.assert_called_once()
    assert out["action_taken"] == "remediated"
    assert out["cleared_broken_localhost"] is True
    assert out["classification"] == "BROKEN_LOCALHOST_PROXY"


def test_guardian_healthy_active_not_cleared_even_with_clear_broken() -> None:
    from src.proxy_drift.guardian import CONFIRM_CLEAR_BROKEN

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:52133", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=True),
        patch("src.proxy_drift.guardian.apply_proxy_fix") as fix,
    ):
        out = run_dead_proxy_guardian_once(
            dry_run=False,
            confirm=CONFIRM_CLEAR_DEAD,
            clear_broken=True,
            confirm_broken=CONFIRM_CLEAR_BROKEN,
            path_health={"proxy_probe_ok": True, "direct_probe_ok": True, "proxy_status": "BOTH_DIRECT_AND_PROXY_WORK"},
        )
    fix.assert_not_called()
    assert out["broken_localhost_proxy"] is False
    assert out["action_taken"] == "none"


def test_guardian_both_probes_fail_clears_with_clear_broken() -> None:
    """Proxy path fail with inconclusive direct still clears under clear_broken."""
    from src.proxy_drift.guardian import CONFIRM_CLEAR_BROKEN

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:52133", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=True),
        patch(
            "src.proxy_drift.guardian.apply_proxy_fix",
            return_value={"action_allowed": True},
        ) as fix,
    ):
        out = run_dead_proxy_guardian_once(
            dry_run=False,
            confirm="",
            clear_broken=True,
            confirm_broken=CONFIRM_CLEAR_BROKEN,
            path_health={"proxy_probe_ok": False, "direct_probe_ok": False, "proxy_status": "BOTH_FAIL"},
        )
    fix.assert_called_once()
    assert out["broken_localhost_proxy"] is True
    assert out["action_taken"] == "remediated"


def test_guardian_hold_direct_clears_healthy_active_localhost() -> None:
    from src.proxy_drift.guardian import CONFIRM_HOLD_DIRECT

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:52133", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=True),
        patch(
            "src.proxy_drift.guardian.apply_proxy_fix",
            return_value={"action_allowed": True},
        ) as fix,
    ):
        out = run_dead_proxy_guardian_once(
            dry_run=False,
            confirm="",
            clear_broken=True,
            hold_direct=True,
            confirm_broken=CONFIRM_HOLD_DIRECT,
            path_health={"proxy_probe_ok": True, "direct_probe_ok": True, "proxy_status": "BOTH_OK"},
        )
    fix.assert_called_once()
    assert out["hold_direct_hit"] is True
    assert out["cleared_hold_direct"] is True
    assert out["action_taken"] == "remediated"


def test_guardian_hold_direct_requires_prefer_direct_token() -> None:
    from src.proxy_drift.guardian import CONFIRM_HOLD_DIRECT

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:52133", auto_config_url=None)
    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.guardian._port_listening", return_value=True),
        patch("src.proxy_drift.guardian.apply_proxy_fix") as fix,
    ):
        out = run_dead_proxy_guardian_once(
            dry_run=False,
            confirm=CONFIRM_CLEAR_DEAD,
            hold_direct=True,
            confirm_broken="",
        )
    fix.assert_not_called()
    assert out["hold_direct_hit"] is True
    assert out["action_taken"] == "blocked"
    assert CONFIRM_HOLD_DIRECT in out["reason"]


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
        "is_broken_localhost_proxy": False,
    }
    healthy = {
        "classification": "NO_PROXY",
        "legacy_classification": "NO_PROXY",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": False,
        "proxy_enable": 0,
        "localhost_port": None,
    }
    with (
        patch("src.proxy_drift.auto_fix.run_dead_proxy_guardian_once", return_value={"action_taken": "preview_only"}),
        patch("src.proxy_drift.auto_fix.apply_proxy_fix", return_value={"action_allowed": True}) as fix,
        patch(
            "src.proxy_drift.auto_fix.read_proxy_drift_status",
            side_effect=[dead, dead, healthy, healthy],
        ),
        patch("src.proxy_drift.auto_fix._install_guardian_loop", return_value={"step": "guardian_install"}),
    ):
        out = run_auto_fix_proxy(dry_run=False, skip_cursor_fix=True, skip_guardian_install=True)
    fix.assert_called_once()
    assert out["outcome"] == "healthy"


def test_auto_fix_broken_localhost_requires_confirm() -> None:
    from src.proxy_drift.auto_fix import run_auto_fix_proxy
    from src.proxy_drift.ensure_health import CONFIRM_PREFER_DIRECT

    broken = {
        "classification": "BROKEN_LOCALHOST_PROXY",
        "legacy_classification": "DEAD_PROXY_CONFIG",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": True,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:57150",
        "localhost_port": 57150,
        "listener_found": True,
        "proxy_probe_ok": False,
        "direct_probe_ok": True,
    }
    with (
        patch("src.proxy_drift.auto_fix.run_dead_proxy_guardian_once", return_value={"action_taken": "none"}),
        patch("src.proxy_drift.auto_fix.apply_proxy_fix") as fix,
        patch("src.proxy_drift.auto_fix.read_proxy_drift_status", return_value=broken),
    ):
        out = run_auto_fix_proxy(
            dry_run=False,
            skip_cursor_fix=True,
            skip_guardian_install=True,
            confirm="",
        )
    fix.assert_not_called()
    assert out["outcome"] == "needs_prefer_direct_confirm"
    prefer_steps = [s for s in out["steps"] if s.get("step") == "prefer_direct"]
    assert prefer_steps and prefer_steps[0]["result"]["action_taken"] == "blocked"
    assert CONFIRM_PREFER_DIRECT in prefer_steps[0]["result"]["reason"]


def test_auto_fix_broken_localhost_clears_with_confirm_without_prefer_direct_flag() -> None:
    from src.proxy_drift.auto_fix import run_auto_fix_proxy
    from src.proxy_drift.ensure_health import CONFIRM_PREFER_DIRECT

    broken = {
        "classification": "BROKEN_LOCALHOST_PROXY",
        "legacy_classification": "DEAD_PROXY_CONFIG",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": True,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:57150",
        "localhost_port": 57150,
        "listener_found": True,
        "proxy_probe_ok": False,
        "direct_probe_ok": True,
    }
    healthy = {
        "classification": "NO_PROXY",
        "legacy_classification": "NO_PROXY",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": False,
        "proxy_enable": 0,
        "proxy_server": None,
        "localhost_port": None,
        "listener_found": None,
    }
    with (
        patch("src.proxy_drift.auto_fix.run_dead_proxy_guardian_once", return_value={"action_taken": "none"}),
        patch(
            "src.proxy_drift.auto_fix.apply_proxy_fix",
            return_value={"action_taken": "applied", "action_allowed": True},
        ) as fix,
        patch(
            "src.proxy_drift.auto_fix.read_proxy_drift_status",
            side_effect=[broken, broken, broken, healthy],
        ),
    ):
        out = run_auto_fix_proxy(
            dry_run=False,
            skip_cursor_fix=True,
            skip_guardian_install=True,
            prefer_direct=False,
            confirm=CONFIRM_PREFER_DIRECT,
        )
    fix.assert_called_once()
    assert out["outcome"] == "healthy"
    prefer_steps = [s for s in out["steps"] if s.get("step") == "prefer_direct"]
    assert prefer_steps and prefer_steps[0]["result"].get("cleared_broken_localhost") is True


def test_auto_fix_healthy_active_localhost_not_cleared_without_prefer_direct() -> None:
    from src.proxy_drift.auto_fix import run_auto_fix_proxy

    active = {
        "classification": "KNOWN_DEV_PROXY",
        "legacy_classification": "KNOWN_DEV_PROXY",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": False,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:57150",
        "localhost_port": 57150,
        "listener_found": True,
        "proxy_probe_ok": True,
        "direct_probe_ok": True,
    }
    with (
        patch("src.proxy_drift.auto_fix.run_dead_proxy_guardian_once", return_value={"action_taken": "none"}),
        patch("src.proxy_drift.auto_fix.apply_proxy_fix") as fix,
        patch("src.proxy_drift.auto_fix.read_proxy_drift_status", return_value=active),
    ):
        out = run_auto_fix_proxy(
            dry_run=False,
            skip_cursor_fix=True,
            skip_guardian_install=True,
            prefer_direct=False,
            confirm="PREFER_DIRECT_WININET",
        )
    fix.assert_not_called()
    assert out["outcome"] == "localhost_proxy_active"


def test_read_proxy_drift_status_uses_path_health_inject() -> None:
    from src.proxy_drift.auto_fix import read_proxy_drift_status

    reg = MagicMock(proxy_enable=1, proxy_server="127.0.0.1:57150", auto_config_url=None)
    with (
        patch("src.proxy_drift.auto_fix.read_proxy_registry", return_value=reg),
        patch("src.proxy_drift.auto_fix._port_listening", return_value=True),
    ):
        out = read_proxy_drift_status(
            path_health={"proxy_probe_ok": False, "direct_probe_ok": True, "proxy_status": "DIRECT_ONLY_WORKS"}
        )
    assert out["classification"] == "BROKEN_LOCALHOST_PROXY"
    assert out["is_broken_localhost_proxy"] is True
    assert out["legacy_classification"] == "DEAD_PROXY_CONFIG"
    assert out["proxy_status"] == "DIRECT_ONLY_WORKS"


def test_ensure_proxy_health_dry_run_skips_prefer_direct_mutation(tmp_path, monkeypatch) -> None:
    from src.proxy_drift.ensure_health import CONFIRM_PREFER_DIRECT, run_ensure_proxy_health

    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    active = {
        "classification": "LOCAL_PROXY_ACTIVE",
        "legacy_classification": "LOCAL_PROXY_ACTIVE",
        "is_dead_localhost_proxy": False,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:54305",
        "localhost_port": 54305,
        "listener_found": True,
    }
    with (
        patch("src.proxy_drift.ensure_health.run_auto_fix_proxy", return_value={"outcome": "healthy"}) as auto,
        patch("src.proxy_drift.ensure_health.apply_proxy_fix") as fix,
        patch("src.proxy_drift.ensure_health.read_proxy_drift_status", return_value=active),
        patch(
            "src.proxy_drift.ensure_health.observability_install_status",
            return_value={"fully_installed": True, "guardian_present": True, "boot_trace_present": True},
        ),
        patch("src.proxy_drift.ensure_health.install_startup_observability") as install,
    ):
        out = run_ensure_proxy_health(
            dry_run=True,
            prefer_direct=True,
            confirm=CONFIRM_PREFER_DIRECT,
            skip_cursor_fix=True,
        )
    auto.assert_called_once()
    fix.assert_not_called()
    install.assert_not_called()
    assert out["outcome"] == "localhost_proxy_active"
    prefer_steps = [s for s in out["steps"] if s.get("step") == "prefer_direct"]
    assert prefer_steps and prefer_steps[0]["result"]["action_taken"] == "preview_only"


def test_ensure_proxy_health_prefer_direct_requires_confirm(tmp_path, monkeypatch) -> None:
    from src.proxy_drift.ensure_health import run_ensure_proxy_health

    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    active = {
        "classification": "LOCAL_PROXY_ACTIVE",
        "legacy_classification": "LOCAL_PROXY_ACTIVE",
        "is_dead_localhost_proxy": False,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:54305",
        "localhost_port": 54305,
        "listener_found": True,
    }
    with (
        patch("src.proxy_drift.ensure_health.run_auto_fix_proxy", return_value={"outcome": "healthy"}),
        patch("src.proxy_drift.ensure_health.apply_proxy_fix") as fix,
        patch("src.proxy_drift.ensure_health.read_proxy_drift_status", return_value=active),
        patch(
            "src.proxy_drift.ensure_health.observability_install_status",
            return_value={"fully_installed": True, "guardian_present": True, "boot_trace_present": True},
        ),
    ):
        out = run_ensure_proxy_health(dry_run=False, prefer_direct=True, confirm="", skip_cursor_fix=True)
    fix.assert_not_called()
    assert out["outcome"] == "needs_prefer_direct_confirm"


def test_ensure_proxy_health_prefer_direct_applies_with_token(tmp_path, monkeypatch) -> None:
    from src.proxy_drift.ensure_health import CONFIRM_PREFER_DIRECT, run_ensure_proxy_health

    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    active = {
        "classification": "LOCAL_PROXY_ACTIVE",
        "legacy_classification": "LOCAL_PROXY_ACTIVE",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": False,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:54305",
        "localhost_port": 54305,
        "listener_found": True,
    }
    healthy = {
        "classification": "NO_PROXY",
        "legacy_classification": "NO_PROXY",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": False,
        "proxy_enable": 0,
        "proxy_server": None,
        "localhost_port": None,
        "listener_found": None,
    }
    with (
        patch("src.proxy_drift.ensure_health.run_auto_fix_proxy", return_value={"outcome": "healthy"}),
        patch(
            "src.proxy_drift.ensure_health.apply_proxy_fix",
            return_value={"action_taken": "applied", "action_allowed": True},
        ) as fix,
        patch(
            "src.proxy_drift.ensure_health.read_proxy_drift_status",
            side_effect=[active, active, healthy],
        ),
        patch(
            "src.proxy_drift.ensure_health.observability_install_status",
            return_value={"fully_installed": True, "guardian_present": True, "boot_trace_present": True},
        ),
    ):
        out = run_ensure_proxy_health(
            dry_run=False,
            prefer_direct=True,
            confirm=CONFIRM_PREFER_DIRECT,
            skip_cursor_fix=True,
        )
    fix.assert_called_once()
    assert out["outcome"] == "healthy"


def test_ensure_proxy_health_broken_clears_with_confirm_without_prefer_direct_flag(tmp_path, monkeypatch) -> None:
    from src.proxy_drift.ensure_health import CONFIRM_PREFER_DIRECT, run_ensure_proxy_health

    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    broken = {
        "classification": "BROKEN_LOCALHOST_PROXY",
        "legacy_classification": "DEAD_PROXY_CONFIG",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": True,
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:57150",
        "localhost_port": 57150,
        "listener_found": True,
        "proxy_probe_ok": False,
        "direct_probe_ok": True,
    }
    healthy = {
        "classification": "NO_PROXY",
        "legacy_classification": "NO_PROXY",
        "is_dead_localhost_proxy": False,
        "is_broken_localhost_proxy": False,
        "proxy_enable": 0,
        "proxy_server": None,
        "localhost_port": None,
        "listener_found": None,
    }
    with (
        patch("src.proxy_drift.ensure_health.run_auto_fix_proxy", return_value={"outcome": "needs_prefer_direct_confirm"}),
        patch(
            "src.proxy_drift.ensure_health.apply_proxy_fix",
            return_value={"action_taken": "applied", "action_allowed": True},
        ) as fix,
        patch(
            "src.proxy_drift.ensure_health.read_proxy_drift_status",
            side_effect=[broken, broken, healthy],
        ),
        patch(
            "src.proxy_drift.ensure_health.observability_install_status",
            return_value={"fully_installed": True, "guardian_present": True, "boot_trace_present": True},
        ),
    ):
        out = run_ensure_proxy_health(
            dry_run=False,
            prefer_direct=False,
            confirm=CONFIRM_PREFER_DIRECT,
            skip_cursor_fix=True,
        )
    fix.assert_called_once()
    assert out["outcome"] == "healthy"
    prefer_steps = [s for s in out["steps"] if s.get("step") == "prefer_direct"]
    assert prefer_steps and prefer_steps[0]["result"].get("cleared_broken_localhost") is True


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


def test_boot_trace_task_preview_uses_expected_command() -> None:
    preview = preview_install_boot_trace_task(duration=240, interval=3)
    assert preview["task_name"] == "WNRT-ProxyBootTrace"
    assert preview["trigger"] == "ONLOGON"
    assert preview["confirmation_required"] == BOOT_TRACE_CONFIRM_INSTALL
    assert preview["command"] == build_boot_trace_task_command(duration=240, interval=3)
    assert "--duration 240 --interval 3" in preview["command"]


def test_boot_trace_task_falls_back_to_startup_hook_on_access_denied(tmp_path: Path) -> None:
    fake_proc = MagicMock(returncode=1, stdout="", stderr="ERROR: Access is denied.")
    with (
        patch("src.proxy_drift.boot_trace_task.subprocess.run", return_value=fake_proc),
        patch("src.proxy_drift.boot_trace_task.startup_hook_path", return_value=tmp_path / "WNRT-ProxyBootTrace.cmd"),
        patch("src.proxy_drift.boot_trace_task.write_startup_hook", return_value=tmp_path / "WNRT-ProxyBootTrace.cmd"),
    ):
        result = install_boot_trace_task(
            duration=240,
            interval=3,
            confirm=BOOT_TRACE_CONFIRM_INSTALL,
            dry_run=False,
        )
    assert result["action_taken"] == "installed"
    assert result["actual_method"] == "startup_hook"
    assert result["fallback_used"] is True


def test_boot_trace_uninstall_succeeds_when_only_startup_hook_removed() -> None:
    fake_proc = MagicMock(returncode=1, stdout="", stderr="ERROR: The system cannot find the file specified.")
    with (
        patch("src.proxy_drift.boot_trace_task.subprocess.run", return_value=fake_proc),
        patch("src.proxy_drift.boot_trace_task.remove_startup_hook", return_value=True),
    ):
        result = uninstall_boot_trace_task(confirm="UNINSTALL_BOOT_TRACE_TASK", dry_run=False)
    assert result["action_taken"] == "uninstalled"
    assert result["startup_hook_removed"] is True


def test_startup_observability_report_summarizes_trace(tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        "\n".join(
            [
                '{"timestamp_utc":"2026-07-07T04:14:00Z","wininet":{"proxy_enable":0,"proxy_server":null},"listener_found":false,"classification":{"classification":"NO_PROXY"},"delta_events":["initial_sample"]}',
                '{"timestamp_utc":"2026-07-07T04:14:03Z","wininet":{"proxy_enable":1,"proxy_server":"127.0.0.1:6000"},"listener_found":true,"classification":{"classification":"KNOWN_DEV_PROXY"},"delta_events":["proxy_enable_changed","proxy_server_changed","listener_appeared"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = summarize_boot_trace(trace)
    assert summary["samples"] == 2
    assert summary["final_classification"] == "KNOWN_DEV_PROXY"
    assert "proxy_server_changed" in summary["delta_events_seen"]


def test_dns_primary_off_subnet_flagged() -> None:
    from src.proxy_drift.dns_health import assess_dns_mismatch

    out = assess_dns_mismatch(
        interface_ipv4="192.168.68.52",
        gateway="192.168.68.1",
        dns_servers=["192.168.1.1", "192.168.68.1"],
    )
    assert out["classification"] == "DNS_PRIMARY_OFF_SUBNET"
    assert out["primary_off_subnet"] is True
    assert "fix-dns" in out["recommended_action"]


def test_dns_same_subnet_ok() -> None:
    from src.proxy_drift.dns_health import assess_dns_mismatch

    out = assess_dns_mismatch(
        interface_ipv4="192.168.68.52",
        gateway="192.168.68.1",
        dns_servers=["192.168.68.1", "1.1.1.1"],
    )
    assert out["classification"] == "DNS_OK"
    assert out["primary_off_subnet"] is False

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard.control import run_proxy_guard_control
from src.proxy_guard.models import ProxySnapshot
from src.proxy_guard.policy import ProxyGuardPolicy


def _snap(enabled: bool, server: str | None) -> ProxyRegistrySnapshot:
    return ProxyRegistrySnapshot(
        proxy_enable=1 if enabled else 0,
        proxy_server=server,
        auto_config_url=None,
        auto_detect=0,
    )


def _lkg() -> ProxySnapshot:
    return ProxySnapshot(
        proxy_enable=0,
        proxy_server=None,
        proxy_override=None,
        auto_config_url=None,
        auto_detect=0,
        winhttp_proxy="",
        winhttp_direct_access=True,
        winhttp_proxy_server_literal=None,
        git_http_proxy=None,
        git_https_proxy=None,
        npm_proxy=None,
        npm_https_proxy=None,
        user_http_proxy=None,
        user_https_proxy=None,
        user_all_proxy=None,
        user_no_proxy=None,
        captured_at="2026-01-01T00:00:00Z",
    )


def _registry_read_side_effect(
    sequence: list[tuple[ProxyRegistrySnapshot, tuple[()]]],
    *,
    steady: tuple[ProxyRegistrySnapshot, tuple[()]] | None = None,
) -> Callable[..., tuple[ProxyRegistrySnapshot, tuple[()]]]:
    """Finite poll sequence then hold last state (avoids exhausted MagicMock side_effect)."""

    hold = steady if steady is not None else sequence[-1]
    state = {"i": 0}

    def _fn(**_kwargs: object) -> tuple[ProxyRegistrySnapshot, tuple[()]]:
        i = state["i"]
        state["i"] += 1
        if i < len(sequence):
            return sequence[i]
        return hold

    return _fn


def _snap_full(reg: ProxyRegistrySnapshot) -> ProxySnapshot:
    return ProxySnapshot(
        proxy_enable=reg.proxy_enable,
        proxy_server=reg.proxy_server,
        proxy_override=reg.proxy_override,
        auto_config_url=reg.auto_config_url,
        auto_detect=reg.auto_detect,
        winhttp_proxy="",
        winhttp_direct_access=True,
        winhttp_proxy_server_literal=None,
        git_http_proxy=None,
        git_https_proxy=None,
        npm_proxy=None,
        npm_https_proxy=None,
        user_http_proxy=None,
        user_https_proxy=None,
        user_all_proxy=None,
        user_no_proxy=None,
        captured_at="2026-01-01T00:00:02Z",
    )


@patch("src.proxy_guard.guard.capture_proxy_snapshot")
@patch("src.proxy_guard.guard.execute_lkg_snapshot_rollback")
@patch("src.proxy_guard.guard.load_lkg_snapshot")
@patch("src.proxy_guard.guard._safe_listen_attribution")
@patch("src.proxy_guard.guard.read_proxy_registry_with_retries")
def test_registry_change_blocked_triggers_rollback_dry_run(
    mock_read,
    mock_safe_attr,
    mock_lkg_load,
    mock_rollback,
    mock_cap,
    tmp_path: Path,
) -> None:
    off = _snap(False, None)
    on = _snap(True, "127.0.0.1:65000")
    after = _snap(False, None)
    mock_read.side_effect = _registry_read_side_effect(
        [(off, ()), (off, ()), (on, ()), (after, ())],
        steady=(after, ()),
    )
    mock_safe_attr.return_value = (
        {
            "port": 65000,
            "owners": [{"process_name": "unauthorized.exe", "pid": 1234}],
            "notes": [],
        },
        (),
    )
    mock_cap.side_effect = lambda **kw: _snap_full(kw["registry_snapshot"])
    mock_lkg_load.return_value = _lkg()
    mock_rollback.return_value = {
        "rollback_kind": "lkg_restore",
        "skipped": False,
        "success": True,
        "wininet_reg": [],
        "winhttp_restore": None,
    }

    policy = ProxyGuardPolicy(
        source_path=tmp_path / "p.json",
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
    )
    log = tmp_path / "logs" / "c.jsonl"
    run_proxy_guard_control(
        interval=0.01,
        once=False,
        auto_rollback=True,
        policy=policy,
        jsonl_path=log,
        dry_run_rollback=True,
        run=subprocess.run,
        exit_after_registry_change_events=1,
        repo_root=tmp_path,
    )
    text = log.read_text(encoding="utf-8")
    assert "registry_change" in text
    assert '"decision": "blocked"' in text
    assert '"action": "rollback"' in text
    mock_rollback.assert_called_once()
    assert mock_rollback.call_args.kwargs["dry_run"] is True


@patch("src.proxy_guard.guard.capture_proxy_snapshot")
@patch("src.proxy_guard.guard.execute_lkg_snapshot_rollback")
@patch("src.proxy_guard.guard.load_lkg_snapshot")
@patch("src.proxy_guard.guard._safe_listen_attribution")
@patch("src.proxy_guard.guard.read_proxy_registry_with_retries")
def test_allowed_no_rollback(mock_read, mock_safe_attr, mock_lkg_load, mock_rollback, mock_cap, tmp_path: Path) -> None:
    """Allowed process still triggers dry-run rollback preview when loopback path is non-operational."""
    a = _snap(False, None)
    b = _snap(True, "127.0.0.1:65001")
    mock_read.side_effect = _registry_read_side_effect(
        [(a, ()), (a, ()), (b, ())],
        steady=(b, ()),
    )
    mock_safe_attr.return_value = (
        {
            "port": 65001,
            "owners": [{"process_name": "allowed.exe", "pid": 1}],
            "notes": [],
        },
        (),
    )
    mock_cap.side_effect = lambda **kw: _snap_full(kw["registry_snapshot"])
    mock_lkg_load.return_value = _lkg()
    mock_rollback.return_value = {
        "rollback_kind": "lkg_restore",
        "skipped": False,
        "success": True,
        "wininet_reg": [],
        "winhttp_restore": None,
    }
    policy = ProxyGuardPolicy(
        source_path=tmp_path / "p.json",
        allowed_process_name_substrings=("allowed",),
        allowed_process_names_exact=("python.exe", "allowed.exe"),
        allow_when_attribution_empty=False,
    )
    log = tmp_path / "logs" / "a.jsonl"
    run_proxy_guard_control(
        interval=0.01,
        once=False,
        auto_rollback=True,
        policy=policy,
        jsonl_path=log,
        dry_run_rollback=True,
        run=subprocess.run,
        exit_after_registry_change_events=1,
        repo_root=tmp_path,
    )
    mock_rollback.assert_called_once()
    assert mock_rollback.call_args.kwargs["dry_run"] is True
    text = log.read_text(encoding="utf-8")
    assert "registry_change" in text
    assert '"decision": "blocked"' in text
    assert "loopback_proxy_path_non_operational" in text

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard.control import run_proxy_guard_control
from src.proxy_guard.policy import ProxyGuardPolicy


def _snap(enabled: bool, server: str | None) -> ProxyRegistrySnapshot:
    return ProxyRegistrySnapshot(
        proxy_enable=1 if enabled else 0,
        proxy_server=server,
        auto_config_url=None,
        auto_detect=0,
    )


@patch("src.proxy_guard.service.execute_low_risk_proxy_rollback")
@patch("src.proxy_guard.service._safe_attribution")
@patch("src.proxy_guard.service.read_proxy_registry_with_retries")
def test_registry_change_blocked_triggers_rollback_dry_run(
    mock_read,
    mock_safe_attr,
    mock_rollback,
    tmp_path: Path,
) -> None:
    off = _snap(False, None)
    on = _snap(True, "127.0.0.1:65000")
    after = _snap(False, None)
    mock_read.side_effect = [
        (off, ()),
        (off, ()),
        (on, ()),
        (after, ()),
    ]
    mock_safe_attr.return_value = (
        {
            "port": 65000,
            "owners": [{"process_name": "unauthorized.exe", "pid": 1234}],
            "notes": [],
        },
        (),
    )
    mock_rollback.return_value = {
        "wininet_reg": [],
        "winhttp_reset": {"argv": ["netsh", "winhttp", "reset", "proxy"]},
        "wininet_skipped_already_cleared": False,
    }

    policy = ProxyGuardPolicy(
        source_path=tmp_path / "p.json",
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
    )
    log = tmp_path / "c.jsonl"
    run_proxy_guard_control(
        interval=0.01,
        once=False,
        auto_rollback=True,
        policy=policy,
        jsonl_path=log,
        dry_run_rollback=True,
        run=subprocess.run,
        exit_after_registry_change_events=1,
    )
    text = log.read_text(encoding="utf-8")
    assert "registry_change" in text
    assert '"decision": "blocked"' in text
    assert '"action": "rollback"' in text
    mock_rollback.assert_called_once()


@patch("src.proxy_guard.service._safe_attribution")
@patch("src.proxy_guard.service.read_proxy_registry_with_retries")
def test_allowed_no_rollback(mock_read, mock_safe_attr, tmp_path: Path) -> None:
    a = _snap(False, None)
    b = _snap(True, "127.0.0.1:65001")
    mock_read.side_effect = [(a, ()), (a, ()), (b, ())]
    mock_safe_attr.return_value = (
        {
            "port": 65001,
            "owners": [{"process_name": "allowed.exe", "pid": 1}],
            "notes": [],
        },
        (),
    )
    policy = ProxyGuardPolicy(
        source_path=tmp_path / "p.json",
        allowed_process_name_substrings=("allowed",),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
    )
    log = tmp_path / "a.jsonl"
    with patch("src.proxy_guard.service.execute_low_risk_proxy_rollback") as mock_rb:
        run_proxy_guard_control(
            interval=0.01,
            once=False,
            auto_rollback=True,
            policy=policy,
            jsonl_path=log,
            dry_run_rollback=True,
            run=subprocess.run,
            exit_after_registry_change_events=1,
        )
    mock_rb.assert_not_called()
    assert '"decision": "allowed"' in log.read_text(encoding="utf-8")

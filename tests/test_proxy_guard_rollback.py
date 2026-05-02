from __future__ import annotations

from src.proxy_guard.rollback import execute_low_risk_proxy_rollback, run_netsh_winhttp_reset_proxy


def test_execute_low_risk_proxy_rollback_dry_run_shape() -> None:
    blob = execute_low_risk_proxy_rollback(dry_run=True, clear_proxy_server_value=True, reset_winhttp=True)
    assert "wininet_reg" in blob
    assert "wininet_skipped_already_cleared" in blob
    assert blob["winhttp_reset"]["argv"][:3] == ["netsh", "winhttp", "reset"]


def test_netsh_dry_run_has_zero_rc() -> None:
    row = run_netsh_winhttp_reset_proxy(dry_run=True)
    assert row["returncode"] == 0

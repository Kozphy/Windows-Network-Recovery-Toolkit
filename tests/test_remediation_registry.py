from __future__ import annotations

from platform_core.remediation_registry import (
    canonical_action_name,
    get_remediation_action,
    list_script_basenames,
)


def test_canonical_aliases() -> None:
    assert canonical_action_name("reset_firewall") == "firewall_reset_manual_only"
    assert canonical_action_name("reset_winsock") == "winsock_reset"


def test_firewall_manual_high_risk_meta() -> None:
    d = get_remediation_action("reset_firewall")
    assert d is not None
    assert d.risk_level == "high"
    assert d.manual_only is True
    assert d.api_execute_allowed is False


def test_reset_dns_allowlisted_basename() -> None:
    d = get_remediation_action("reset_dns")
    assert d and d.script_path == "reset_dns.bat"
    assert "reset_dns.bat" in list_script_basenames()


def test_arbitrary_forbidden() -> None:
    d = get_remediation_action("arbitrary_command")
    assert d is not None
    assert d.risk_level == "forbidden"

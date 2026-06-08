from __future__ import annotations

import pytest

from src.proxy_guard.remediation import (
    CONFIRMATION_PHRASE,
    build_user_proxy_disable_mutations,
    get_remediation_action,
    remediation_action_catalog,
    validate_action_confirmation,
)
from src.repair.executor import apply_mutations
from src.repair.policy import assert_no_firewall_reset_in_preview


def test_firewall_preview_guard() -> None:
    assert_no_firewall_reset_in_preview("")
    with pytest.raises(ValueError):
        assert_no_firewall_reset_in_preview("run reset_firewall.bat")


def test_apply_mutations_dry_run_returns_zero_codes() -> None:
    mutations, texts = build_user_proxy_disable_mutations(clear_proxy_server_value=False)
    preview = "\n".join(texts)
    assert_no_firewall_reset_in_preview(preview)
    results = apply_mutations(mutations, dry_run=True)
    assert all(r.returncode == 0 for r in results)


def test_clear_server_adds_second_mutation() -> None:
    a, _ta = build_user_proxy_disable_mutations(
        clear_proxy_server_value=False,
        clear_autoconfig_url=False,
    )
    b, tb = build_user_proxy_disable_mutations(
        clear_proxy_server_value=True,
        clear_autoconfig_url=False,
    )
    assert len(a) == 1
    assert len(b) == 2
    assert "delete" in " ".join(tb).lower()


def test_proxy_disable_allowlist_requires_confirmation() -> None:
    action = get_remediation_action("disable_wininet_proxy")
    assert action is not None
    assert action.required_confirmation == "DISABLE_WININET_PROXY"
    assert "ProxyEnable" in action.allowed_registry_fields
    assert "ProxyServer" in action.allowed_registry_fields

    preview = validate_action_confirmation(
        action_id="disable_wininet_proxy",
        dry_run=True,
        confirmation="",
        requested_registry_fields=("ProxyEnable",),
    )
    assert preview[0] == "PREVIEW"

    blocked = validate_action_confirmation(
        action_id="disable_wininet_proxy",
        dry_run=False,
        confirmation="",
        requested_registry_fields=("ProxyEnable",),
    )
    assert blocked[0] == "BLOCK"
    assert blocked[1] == "missing_confirmation"

    allowed = validate_action_confirmation(
        action_id="disable_wininet_proxy",
        dry_run=False,
        confirmation=CONFIRMATION_PHRASE,
        requested_registry_fields=("ProxyEnable",),
    )
    assert allowed[0] == "ALLOW"


def test_dangerous_actions_are_blocked() -> None:
    catalog = {row.action_id: row for row in remediation_action_catalog()}
    for action_id in (
        "reset_firewall",
        "disable_adapter",
        "kill_process",
        "delete_certificate",
        "broad_registry_cleanup",
    ):
        row = catalog[action_id]
        assert row.blocked_reason
        decision, reason, _action = validate_action_confirmation(
            action_id=action_id,
            dry_run=False,
            confirmation="anything",
            requested_registry_fields=(),
        )
        assert decision == "BLOCK"
        assert reason == row.blocked_reason


def test_proxy_disable_blocks_non_allowlisted_registry_field() -> None:
    decision, reason, _action = validate_action_confirmation(
        action_id="disable_wininet_proxy",
        dry_run=False,
        confirmation=CONFIRMATION_PHRASE,
        requested_registry_fields=("ProxyEnable", "ProxyOverride"),
    )
    assert decision == "BLOCK"
    assert "ProxyOverride" in reason

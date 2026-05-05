"""Structured platform remediation gates vs hypothesis ``ALLOW`` (orthogonal layers).

Mocks: none — :func:`platform_core.policy.engine.evaluate` is pure/deterministic for these tuples.

Scenario catalog:

┌─────────────────────────────────────┬────────────────────────────────────────┐
│ platform.safe_dns_operator_previews │ operator may preview reset_dns only    │
│ platform.unsafe_firewall_blocked    │ structured preview + execute denied for FW  │
│ platform.admin_proxy_needs_phrase  │ RUN_PROXY_RESET gating surfaced        │
└─────────────────────────────────────┴────────────────────────────────────────┘
"""

from __future__ import annotations

from platform_core.policy.engine import OperatorContext, evaluate


def test_platform_policy_allows_preview_for_safe_dns_reset_operator() -> None:
    g = evaluate({}, "reset_dns", OperatorContext(role="operator", surface="api"))
    assert g.preview_allowed is True
    assert g.execute_allowed is False


def test_platform_policy_blocks_firewall_execution_even_for_admin() -> None:
    g = evaluate({}, "reset_firewall", OperatorContext(role="admin", surface="api"))
    assert g.execute_allowed is False
    assert g.preview_allowed is False
    assert "manual_only_registry_entry" in g.reason_codes
    assert "high_risk_blocked_from_platform" in g.reason_codes or "classic_gate_denied" in g.reason_codes


def test_platform_policy_proxy_reset_requires_confirmation_phrase() -> None:
    g = evaluate({}, "reset_proxy", OperatorContext(role="admin", surface="api"))
    assert g.preview_allowed is True
    assert g.execute_allowed is True
    assert g.required_confirmation == "RUN_PROXY_RESET"
    assert "confirmation_phrase_required" in g.reason_codes


def test_platform_policy_unknown_action_always_blocked() -> None:
    g = evaluate({}, "__not_registered__action__", OperatorContext(role="admin", surface="api"))
    assert g.preview_allowed is False
    assert g.execute_allowed is False
    assert "unknown_action" in g.reason_codes

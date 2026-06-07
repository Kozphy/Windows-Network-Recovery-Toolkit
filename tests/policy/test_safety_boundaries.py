"""Safety boundary regression tests for policy gates and remediation registry.

These tests prove destructive or high-risk actions cannot slip through policy
even when operator confidence or role hints suggest otherwise.
"""

from __future__ import annotations

import pytest

from platform_core.models import FailureEvent, RemediationPolicy
from platform_core.policy import (
    OperatorContext,
    build_preview,
    evaluate,
    evaluate_action,
    is_shell_injection,
    validate_confirmation_phrase,
)
from platform_core.remediation_registry import get_remediation_action


@pytest.mark.parametrize(
    "action_key",
    [
        "process_kill_forbidden",
        "adapter_disable_forbidden",
        "arbitrary_command_forbidden",
    ],
)
def test_forbidden_actions_never_allow_execute(action_key: str) -> None:
    ctx = OperatorContext(role="admin", surface="api")
    gate = evaluate({"summary": "high confidence fixture"}, action_key, ctx)
    assert gate.execute_allowed is False
    assert gate.preview_allowed is False
    assert gate.reason_codes
    assert any(
        code in gate.reason_codes
        for code in (
            "execute_blocked_high_or_forbidden_tier",
            "classic_gate_denied",
            "forbidden_action",
            "surface_not_allowed",
        )
    )


def test_firewall_reset_manual_only_blocks_api_execute() -> None:
    ctx = OperatorContext(role="admin", surface="api")
    gate = evaluate({"summary": "firewall drift"}, "reset_firewall", ctx)
    assert gate.execute_allowed is False
    assert "firewall_or_adapter_manual_only" in gate.reason_codes


def test_high_risk_blocked_even_for_admin() -> None:
    pd = evaluate_action("firewall_reset_manual_only", "api")
    assert pd.allowed is False
    assert pd.effective_risk in {"high", "forbidden"}


def test_block_actions_remain_blocked_when_confidence_signal_is_high() -> None:
    ctx = OperatorContext(role="admin", surface="api")
    signals = {"summary": "99% confidence malicious proxy", "confidence": 0.99}
    gate = evaluate(signals, "process_kill_forbidden", ctx)
    assert gate.execute_allowed is False
    assert gate.preview_allowed is False


def test_preview_does_not_imply_execute_for_operator() -> None:
    ctx = OperatorContext(role="operator", surface="api")
    gate = evaluate({"summary": "dns issue"}, "reset_dns", ctx)
    assert gate.preview_allowed is True
    assert gate.execute_allowed is False
    assert "operator_may_preview_only_live_requires_admin" in gate.reason_codes


def test_allow_still_requires_confirmation_phrase_for_gated_actions() -> None:
    defn = get_remediation_action("reset_dns")
    assert defn is not None
    assert defn.confirmation_phrase
    assert validate_confirmation_phrase("reset_dns", "") is False
    assert validate_confirmation_phrase("reset_dns", defn.confirmation_phrase) is True


def test_registry_mutation_actions_require_non_empty_confirmation() -> None:
    for key in ("reset_proxy", "stop_proxy_listener", "stop_proxy_reverter"):
        defn = get_remediation_action(key)
        assert defn is not None, key
        assert defn.requires_confirmation is True
        assert defn.confirmation_phrase.strip() != ""


def test_build_preview_is_non_mutating_snapshot() -> None:
    event = FailureEvent(
        event_id="safety-preview-1",
        endpoint_id="ep-safety",
        severity="low",
        category="dns",
        confidence=0.9,
        summary="fixture",
        recommended_action_key="reset_dns",
    )
    preview = build_preview(event, "reset_dns", requested_surface="api")
    assert preview.commands_preview
    assert preview.allowed_by_policy is True
    assert preview.requires_typed_confirmation is True


def test_arbitrary_shell_flag_is_dead_and_blocks() -> None:
    ctx = OperatorContext(role="admin", surface="api")
    gate = evaluate({"summary": "shell"}, "inspect_proxy", ctx, allow_arbitrary_shell=True)
    assert gate.execute_allowed is False
    assert gate.preview_allowed is False
    assert "arbitrary_shell_forbidden_even_if_requested" in gate.reason_codes


@pytest.mark.parametrize(
    "text",
    [
        "cmd & echo pwn",
        "echo hi; rm -rf /",
        "echo `whoami`",
        "line1\nline2",
    ],
)
def test_shell_injection_detector_rejects_metacharacters(text: str) -> None:
    assert is_shell_injection(text) is True


def test_viewer_cannot_preview_or_execute() -> None:
    ctx = OperatorContext(role="viewer", surface="api")
    gate = evaluate({"summary": "viewer probe"}, "inspect_proxy", ctx)
    assert gate.preview_allowed is False
    assert gate.execute_allowed is False
    assert "viewer_preview_blocked" in gate.reason_codes


def test_custom_policy_can_forbid_low_risk_action() -> None:
    pol = RemediationPolicy(forbidden_actions=frozenset({"reset_dns"}))
    pd = evaluate_action("reset_dns", "api", pol)
    assert pd.allowed is False
    assert pd.reason == "action_forbidden_by_policy"

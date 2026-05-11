"""Phase 1: policy vocabulary, destructive-action gates, replay without live probes.

These tests are offline-only and must not spawn repair subprocesses or open network sockets.
"""

from __future__ import annotations

import socket
import subprocess
from unittest.mock import MagicMock

import pytest

from platform_core.policy.engine import OperatorContext, StructuredPolicyDecision, evaluate
from platform_core.remediation_registry import canonical_action_name, get_remediation_action
from platform_core.policy_vocabulary import (
    explain_tri_state,
    product_contract_decision_to_tri_state,
    structured_decision_to_tri_state,
    tri_state_to_product_contract_decision,
)
from platform_core.reasoning_audit import replay_reasoning_record, to_audit_record
from platform_core.reasoning_engine import observation, run_reasoning
from platform_core.reasoning_models import ProofResult


def _admin_api() -> OperatorContext:
    return OperatorContext(role="admin", surface="api")


def test_structured_decision_to_tri_state_allow_when_execute_allowed() -> None:
    d = StructuredPolicyDecision(execute_allowed=True, preview_allowed=True)
    assert structured_decision_to_tri_state(d) == "ALLOW"


def test_structured_decision_to_tri_state_preview_when_execute_denied() -> None:
    d = StructuredPolicyDecision(execute_allowed=False, preview_allowed=True)
    assert structured_decision_to_tri_state(d) == "PREVIEW"


def test_structured_decision_to_tri_state_block_when_both_denied() -> None:
    d = StructuredPolicyDecision(execute_allowed=False, preview_allowed=False)
    assert structured_decision_to_tri_state(d) == "BLOCK"


def test_product_contract_round_trip_preview_only() -> None:
    assert tri_state_to_product_contract_decision("PREVIEW") == "preview_only"
    assert product_contract_decision_to_tri_state("preview_only") == "PREVIEW"


def test_explain_tri_state_non_empty() -> None:
    for tri in ("ALLOW", "PREVIEW", "BLOCK"):
        assert len(explain_tri_state(tri)) > 20


def test_forbidden_remediation_aliases_resolve_to_registry_canonical_rows() -> None:
    """Operator-facing strings must map to real ``_REMEDIATION_REGISTRY`` keys via :func:`canonical_action_name`.

    Policy :func:`~platform_core.policy.engine.evaluate` always normalizes inputs through that helper; these
    assertions catch typos or dropped ``_ACTION_ALIASES`` entries before ``unknown_action`` false negatives.
    """
    pairs = (
        ("process_kill", "process_kill_forbidden"),
        ("kill_process", "process_kill_forbidden"),
        ("certificate_delete", "certificate_delete_forbidden"),
        ("delete_certificate", "certificate_delete_forbidden"),
        ("arbitrary_command", "arbitrary_command_forbidden"),
    )
    for alias, expected_canonical in pairs:
        assert canonical_action_name(alias) == expected_canonical
        defn = get_remediation_action(expected_canonical)
        assert defn is not None, expected_canonical
        assert defn.risk_level == "forbidden"


@pytest.mark.parametrize(
    "canonical_action",
    [
        # Manual-only high risk — canonical remediation registry keys only (see remediation_registry.py).
        "firewall_reset_manual_only",
        # Forbidden tiers and explicit forbids — never rely on undocumented strings here.
        "adapter_disable_forbidden",
        "process_kill_forbidden",
        "certificate_delete_forbidden",
        "arbitrary_command_forbidden",
    ],
)
def test_destructive_or_forbidden_actions_block_api_execute_for_admin(canonical_action: str) -> None:
    """High-risk manual-only and forbidden registry rows must not authorize live execute.

    Inputs are canonical :data:`platform_core.remediation_registry._REMEDIATION_REGISTRY` keys so
    this always exercises the intended :class:`~platform_core.remediation_registry.RemediationActionDef`,
    regardless of caller-side alias hygiene.
    """
    gate = evaluate({}, canonical_action, _admin_api())
    assert gate.execute_allowed is False, f"{canonical_action} must not grant execute_allowed"


@pytest.mark.parametrize(
    "canonical_action",
    [
        "adapter_disable_forbidden",
        "process_kill_forbidden",
        "certificate_delete_forbidden",
        "arbitrary_command_forbidden",
    ],
)
def test_forbidden_actions_also_block_preview(canonical_action: str) -> None:
    """Forbidden-tier actions must not offer even platform preview surfaces (defense-in-depth)."""
    gate = evaluate({}, canonical_action, _admin_api())
    assert gate.preview_allowed is False, f"{canonical_action} must not grant preview_allowed"


@pytest.mark.parametrize(
    ("alias", "canonical_action"),
    [
        ("reset_firewall", "firewall_reset_manual_only"),
        ("process_kill", "process_kill_forbidden"),
        ("kill_process", "process_kill_forbidden"),
        ("certificate_delete", "certificate_delete_forbidden"),
        ("delete_certificate", "certificate_delete_forbidden"),
        ("arbitrary_command", "arbitrary_command_forbidden"),
    ],
)
def test_policy_evaluate_alias_matches_canonical_gate(
    alias: str,
    canonical_action: str,
) -> None:
    """:func:`~platform_core.policy.engine.evaluate` must resolve `_ACTION_ALIASES` the same as a canonical key.

    If this fails, callers using operator-facing strings would hit ``unknown_action`` or diverge from intended defs.
    """
    ctx = _admin_api()
    via_alias = evaluate({}, alias, ctx)
    via_canonical = evaluate({}, canonical_action, ctx)
    assert via_alias.execute_allowed == via_canonical.execute_allowed
    assert via_alias.preview_allowed == via_canonical.preview_allowed
    assert via_alias.risk_tier == via_canonical.risk_tier


def test_firewall_reset_blocks_execute_and_carries_manual_only_reason() -> None:
    gate = evaluate({}, "reset_firewall", _admin_api())
    assert gate.execute_allowed is False
    assert "manual_only_registry_entry" in gate.reason_codes


def test_replay_reasoning_record_does_not_open_socket_or_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replay recomputes from stored observations only — no live machine probes."""

    def _socket_fail(*_a: object, **_k: object) -> MagicMock:
        raise AssertionError("socket must not be used during reasoning replay")

    def _subprocess_fail(*_a: object, **_k: object) -> object:
        raise AssertionError("subprocess must not be used during reasoning replay")

    monkeypatch.setattr(socket, "socket", _socket_fail)
    monkeypatch.setattr(socket, "create_connection", _socket_fail)
    monkeypatch.setattr(subprocess, "run", _subprocess_fail)
    monkeypatch.setattr(subprocess, "Popen", _subprocess_fail)

    proof = ProofResult(hypothesis="browser_proxy_path_regression", status="CONFIRMED", confidence=0.95)
    observations = [
        observation("ping_ok"),
        observation("dns_ok"),
        observation("tcp443_ok"),
        observation("browser_https_failed"),
        observation("wininet_proxy_enabled"),
        observation("proxy_bypass_succeeded"),
        observation("proxied_path_failed"),
    ]
    run = run_reasoning(observations, proof_result=proof, requested_action="restore_proxy")
    record = to_audit_record(run)
    replayed = replay_reasoning_record(record)
    assert replayed.accepted_hypothesis == run.accepted_hypothesis
    assert replayed.policy_decision.outcome == run.policy_decision.outcome

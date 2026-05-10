"""Phase 1: policy vocabulary, destructive-action gates, replay without live probes.

These tests are offline-only and must not spawn repair subprocesses or open network sockets.
"""

from __future__ import annotations

import socket
import subprocess
from unittest.mock import MagicMock

import pytest

from platform_core.policy.engine import OperatorContext, StructuredPolicyDecision, evaluate
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


@pytest.mark.parametrize(
    "action",
    [
        "reset_firewall",
        "firewall_reset_manual_only",
        "adapter_disable_forbidden",
        "process_kill",
        "kill_process",
        "certificate_delete",
        "arbitrary_command",
        "arbitrary_command_forbidden",
    ],
)
def test_destructive_or_forbidden_actions_block_api_execute_for_admin(action: str) -> None:
    """High-risk manual-only, forbidden registry rows, and arbitrary commands must not authorize live execute."""
    gate = evaluate({}, action, _admin_api())
    assert gate.execute_allowed is False, f"{action} must not grant execute_allowed"


@pytest.mark.parametrize(
    "action",
    [
        "adapter_disable_forbidden",
        "process_kill",
        "certificate_delete",
        "arbitrary_command",
    ],
)
def test_forbidden_actions_also_block_preview(action: str) -> None:
    """Forbidden-tier actions must not offer even platform preview surfaces (defense-in-depth)."""
    gate = evaluate({}, action, _admin_api())
    assert gate.preview_allowed is False, f"{action} must not grant preview_allowed"


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

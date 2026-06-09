"""Extended safety contracts for Tier-1 portfolio."""

from __future__ import annotations

from platform_core.policy_model import evaluate_endpoint_policy
from platform_core.evidence_model import can_upgrade_evidence


def test_no_registry_mutation_policy_without_confirmation_path() -> None:
    pol = evaluate_endpoint_policy(
        evidence_level="PROVEN_REGISTRY_WRITER",
        confidence_ordinal=0.9,
        requested_action="reset_proxy",
    )
    assert pol["execute_allowed"] is False
    assert pol["decision"] == "REQUIRE_TYPED_CONFIRMATION"


def test_destructive_action_blocked() -> None:
    pol = evaluate_endpoint_policy(
        evidence_level="FINAL_CAUSATION",
        requested_action="kill_process",
    )
    assert pol["decision"] == "BLOCK_DESTRUCTIVE"
    assert pol["execute_allowed"] is False


def test_correlated_cannot_upgrade_to_proven_without_telemetry() -> None:
    assert not can_upgrade_evidence(
        "CORRELATED",
        "PROVEN_REGISTRY_WRITER",
        has_writer_telemetry=False,
        has_listener_correlation_only=True,
    )

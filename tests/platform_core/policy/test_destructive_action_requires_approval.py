"""Destructive actions require approval."""

from __future__ import annotations

from src.platform_core.contracts import Decision, EvidenceBundle
from src.platform_core.evidence.guards import ProofInputs
from src.platform_core.policy.engine import evaluate_policy


def _decision() -> Decision:
    return Decision(
        decision_id="d1",
        incident_id="i1",
        timestamp_utc="2026-01-01T00:00:00Z",
        incident_type="WININET_PROXY_DRIFT",
        recommended_action="DISABLE",
        confidence=0.9,
        evidence_tier="FINAL_CAUSATION",
    )


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id="b1",
        incident_id="i1",
        created_at="2026-01-01T00:00:00Z",
        tier="FINAL_CAUSATION",
    )


def test_destructive_requires_approval() -> None:
    proof = ProofInputs(
        has_registry_writer_telemetry=True,
        has_process_lineage=True,
        has_timestamp_alignment=True,
        has_path_validation=True,
    )
    pe = evaluate_policy(
        decision=_decision(),
        bundle=_bundle(),
        requested_action="disable_wininet_proxy",
        proof=proof,
    )
    assert pe.requires_approval is True
    assert pe.outcome in {"REQUIRE_HUMAN_APPROVAL", "ROLLBACK_REQUIRED", "PREVIEW_ONLY"}

from types import SimpleNamespace

from src.platform_core.governance.evidence_decision_lifecycle import (
    ClaimStatus,
    VerificationStatus,
    lifecycle_from_risk_decision,
)


def _record(*, proof_tier: str = "T3_CORROBORATED", confidence: float = 0.9):
    return SimpleNamespace(
        incident_id="INC-001",
        evidence_id="ev-INC-001",
        decision_key="decision-001",
        audit_id="audit-001",
        classification="DEAD_PROXY_CONFIG",
        secondary_signals=["wininet_proxy_enabled", "listener_missing"],
        proof_tier=SimpleNamespace(value=proof_tier),
        confidence_score=confidence,
        confidence_label="high" if confidence >= 0.85 else "medium",
        limitations=["No process attribution evidence."],
    )


def test_high_proof_tier_produces_verified_knowledge():
    lifecycle = lifecycle_from_risk_decision(_record())

    assert lifecycle.claim.status == ClaimStatus.SUPPORTED
    assert lifecycle.verification.status == VerificationStatus.VERIFIED
    assert lifecycle.knowledge.valid_for_decision is True
    assert lifecycle.uncertainty.probability_calibrated is False
    assert lifecycle.decision_id == "decision-001"


def test_low_proof_tier_stays_inconclusive():
    lifecycle = lifecycle_from_risk_decision(_record(proof_tier="T1_LOCAL_CONFIG_EVIDENCE", confidence=0.6))

    assert lifecycle.claim.status == ClaimStatus.INCONCLUSIVE
    assert lifecycle.verification.status == VerificationStatus.INCONCLUSIVE
    assert lifecycle.knowledge.valid_for_decision is False
    assert lifecycle.uncertainty.missing_evidence


def test_lifecycle_preserves_limitations():
    lifecycle = lifecycle_from_risk_decision(_record())

    assert "No process attribution evidence." in lifecycle.verification.limitations
    assert "No process attribution evidence." in lifecycle.knowledge.limitations
    assert "No process attribution evidence." in lifecycle.uncertainty.uncertainty_sources

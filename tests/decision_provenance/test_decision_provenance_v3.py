from __future__ import annotations

import pytest

from src.platform_core.governance.approval_record import (
    ApprovalOutcome,
    create_approval,
)
from src.platform_core.governance.proof_tier import ProofTier
from src.platform_core.governance.risk_decision_record_v3 import (
    DecisionStatus,
    upgrade_v2_record,
)
from src.platform_core.reasoning.hypothesis import (
    EvidenceBinding,
    EvidenceRelationship,
    Hypothesis,
    HypothesisStatus,
)
from src.platform_core.reliability.evidence_reliability import (
    EvidenceReliability,
    ReliabilityBand,
)


def _reliability() -> EvidenceReliability:
    return EvidenceReliability(
        source_integrity=90,
        freshness=95,
        collection_reproducibility=85,
        coverage=60,
        contradiction_penalty=0,
        limitations=["Registry writer identity was not observed."],
    )


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        hypothesis_id="HYP-DEAD-LOCAL-PROXY",
        statement="WinINET points to a localhost proxy without a working listener",
        status=HypothesisStatus.SUPPORTED,
        evidence_bindings=[
            EvidenceBinding(
                evidence_id="EVT-LOCALHOST-LISTENER-ABSENT",
                relationship=EvidenceRelationship.SUPPORTS,
                rationale_code="EVT-LOCALHOST-LISTENER-ABSENT",
                weight=90,
            )
        ],
    )


def _v2_record() -> dict[str, object]:
    return {
        "schema_version": "risk_decision_record.v2",
        "incident_id": "INC-59081",
        "evidence_id": "ev-INC-59081",
        "evidence_schema_version": "evidence_bundle.v1",
        "classifier_version": "proxy_classifier.v1",
        "policy_version": "technology_risk_policy.v1",
        "control_set_version": "endpoint_controls.v1",
        "classification": "DEAD_PROXY_CONFIG",
        "secondary_signals": ["WININET_WINHTTP_MISMATCH"],
        "proof_tier": ProofTier.T2_NETWORK_PATH_EVIDENCE,
        "confidence_score": 0.92,
        "risk_rating": "high",
        "recommended_action": "Preview disabling the dead proxy",
        "execution_authority": "preview_only",
        "human_review_required": True,
        "limitations": ["Does not prove malware or MITM."],
        "operator_id": "operator-1",
    }


def test_supported_hypothesis_requires_supporting_evidence() -> None:
    with pytest.raises(ValueError, match="supporting evidence"):
        Hypothesis(
            hypothesis_id="HYP-INVALID",
            statement="Unsupported claim",
            status=HypothesisStatus.SUPPORTED,
        )


def test_reliability_is_separate_from_classifier_confidence() -> None:
    reliability = _reliability()
    assert reliability.score == 82
    assert reliability.overall_band == ReliabilityBand.RELIABLE


def test_v2_upgrade_is_backward_compatible_and_hashes_decision_material() -> None:
    hypothesis = _hypothesis()
    decision = upgrade_v2_record(
        _v2_record(),
        evidence_reliability=_reliability(),
        hypotheses=[hypothesis],
        selected_hypothesis_id=hypothesis.hypothesis_id,
        selection_reason_codes=["HYP-DEAD-PROXY-SUPPORTED"],
    )

    assert decision.schema_version == "risk_decision_record.v3"
    assert decision.decision_status == DecisionStatus.READY_FOR_REVIEW
    assert decision.decision_key
    assert decision.classification == "DEAD_PROXY_CONFIG"
    assert decision.proposed_by == "operator-1"


def test_changed_decision_material_invalidates_approval() -> None:
    hypothesis = _hypothesis()
    decision = upgrade_v2_record(
        _v2_record(),
        evidence_reliability=_reliability(),
        hypotheses=[hypothesis],
        selected_hypothesis_id=hypothesis.hypothesis_id,
    )
    approval = create_approval(
        decision,
        reviewer_id="reviewer-1",
        outcome=ApprovalOutcome.APPROVED,
        reason_codes=["POL-HUMAN-CONFIRMATION-SATISFIED"],
    )

    assert approval.is_current_for(decision)

    decision.recommended_action = "Continue read-only investigation"

    assert not approval.is_current_for(decision)


def test_same_material_produces_same_decision_key() -> None:
    hypothesis = _hypothesis()
    first = upgrade_v2_record(
        _v2_record(),
        evidence_reliability=_reliability(),
        hypotheses=[hypothesis],
        selected_hypothesis_id=hypothesis.hypothesis_id,
    )
    second = upgrade_v2_record(
        _v2_record(),
        evidence_reliability=_reliability(),
        hypotheses=[hypothesis],
        selected_hypothesis_id=hypothesis.hypothesis_id,
    )

    assert first.decision_key == second.decision_key

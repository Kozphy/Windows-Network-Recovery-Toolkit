"""RiskDecisionRecord v3 with hypothesis, reliability, and lifecycle provenance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.platform_core.governance.proof_tier import ProofTier
from src.platform_core.reasoning.hypothesis import Hypothesis
from src.platform_core.reliability.evidence_reliability import EvidenceReliability
from src.platform_core.serialization import content_hash


class DecisionStatus(StrEnum):
    DRAFT = "draft"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTION_PREVIEWED = "execution_previewed"
    EXECUTED = "executed"
    OUTCOME_VERIFIED = "outcome_verified"
    SUPERSEDED = "superseded"
    CLOSED = "closed"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STALE = "stale"


class ExecutionStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    PREVIEWED = "previewed"
    BLOCKED = "blocked"
    EXECUTED = "executed"
    FAILED = "failed"


class OutcomeStatus(StrEnum):
    NOT_VERIFIED = "not_verified"
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    UNCHANGED = "unchanged"
    REGRESSED = "regressed"
    INCONCLUSIVE = "inconclusive"


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class RiskDecisionRecordV3(BaseModel):
    schema_version: str = "risk_decision_record.v3"
    decision_id: str = Field(default_factory=lambda: f"dec-{uuid.uuid4().hex[:12]}")
    incident_id: str
    evidence_id: str
    decision_key: str = ""

    evidence_schema_version: str
    classifier_version: str
    policy_version: str
    control_set_version: str

    hypotheses: list[Hypothesis] = Field(default_factory=list)
    selected_hypothesis_id: str | None = None
    selection_reason_codes: list[str] = Field(default_factory=list)
    evidence_reliability: EvidenceReliability

    classification: str
    secondary_signals: list[str] = Field(default_factory=list)
    proof_tier: ProofTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_rating: str
    recommended_action: str
    execution_authority: str
    human_review_required: bool = True
    limitations: list[str] = Field(default_factory=list)

    decision_status: DecisionStatus = DecisionStatus.DRAFT
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    execution_status: ExecutionStatus = ExecutionStatus.NOT_REQUESTED
    outcome_status: OutcomeStatus = OutcomeStatus.NOT_VERIFIED

    proposed_by: str = "unassigned"
    reviewed_by: str | None = None
    approved_by: str | None = None
    executed_by: str | None = None
    trace_id: str = Field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:12]}")
    parent_decision_id: str | None = None
    supersedes_decision_id: str | None = None
    created_at: str = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_selected_hypothesis(self) -> "RiskDecisionRecordV3":
        ids = {hypothesis.hypothesis_id for hypothesis in self.hypotheses}
        if self.selected_hypothesis_id and self.selected_hypothesis_id not in ids:
            raise ValueError("selected_hypothesis_id must reference a supplied hypothesis")
        if self.approval_status == ApprovalStatus.APPROVED and not self.approved_by:
            raise ValueError("approved decisions require approved_by")
        return self

    def decision_material(self) -> dict[str, Any]:
        """Return immutable material to which approvals and replay bind."""
        return {
            "incident_id": self.incident_id,
            "evidence_id": self.evidence_id,
            "evidence_schema_version": self.evidence_schema_version,
            "classifier_version": self.classifier_version,
            "policy_version": self.policy_version,
            "control_set_version": self.control_set_version,
            "hypotheses": [item.model_dump(mode="json") for item in self.hypotheses],
            "selected_hypothesis_id": self.selected_hypothesis_id,
            "selection_reason_codes": self.selection_reason_codes,
            "evidence_reliability": self.evidence_reliability.model_dump(mode="json"),
            "classification": self.classification,
            "secondary_signals": self.secondary_signals,
            "proof_tier": self.proof_tier.value,
            "confidence_score": self.confidence_score,
            "risk_rating": self.risk_rating,
            "recommended_action": self.recommended_action,
            "execution_authority": self.execution_authority,
            "limitations": self.limitations,
        }

    def refresh_decision_key(self) -> str:
        self.decision_key = content_hash(self.decision_material())
        return self.decision_key


def upgrade_v2_record(
    record: BaseModel | dict[str, Any],
    *,
    evidence_reliability: EvidenceReliability,
    hypotheses: list[Hypothesis] | None = None,
    selected_hypothesis_id: str | None = None,
    selection_reason_codes: list[str] | None = None,
) -> RiskDecisionRecordV3:
    """Upgrade a v2 record without changing the existing v2 implementation."""
    data = record.model_dump(mode="json") if isinstance(record, BaseModel) else dict(record)
    upgraded = RiskDecisionRecordV3(
        incident_id=data["incident_id"],
        evidence_id=data.get("evidence_id") or f"ev-{data['incident_id']}",
        evidence_schema_version=data.get("evidence_schema_version", "evidence_bundle.v1"),
        classifier_version=data.get("classifier_version", "proxy_classifier.v1"),
        policy_version=data.get("policy_version", "technology_risk_policy.v1"),
        control_set_version=data.get("control_set_version", "endpoint_controls.v1"),
        hypotheses=hypotheses or [],
        selected_hypothesis_id=selected_hypothesis_id,
        selection_reason_codes=selection_reason_codes or [],
        evidence_reliability=evidence_reliability,
        classification=data.get("classification", ""),
        secondary_signals=data.get("secondary_signals", []),
        proof_tier=data.get("proof_tier", ProofTier.T0_OBSERVATION_ONLY),
        confidence_score=data.get("confidence_score", 0.5),
        risk_rating=data.get("risk_rating", "medium"),
        recommended_action=data.get("recommended_action", "Continue read-only investigation"),
        execution_authority=data.get("execution_authority", "preview_only"),
        human_review_required=data.get("human_review_required", True),
        limitations=data.get("limitations", []),
        proposed_by=data.get("operator_id", "unassigned"),
    )
    upgraded.decision_status = (
        DecisionStatus.READY_FOR_REVIEW
        if upgraded.hypotheses and upgraded.selected_hypothesis_id
        else DecisionStatus.EVIDENCE_INCOMPLETE
    )
    upgraded.refresh_decision_key()
    return upgraded

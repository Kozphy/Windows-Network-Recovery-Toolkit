"""Evidence Case — typed pipeline models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.platform_core.contracts import (
    AuditRecord,
    Decision,
    EvidenceBundle,
    Hypothesis,
    IncidentOutcome,
    LearningRecord,
    PolicyEvaluation,
)

EVIDENCE_CASE_SCHEMA_VERSION = "evidence_case.v1"


class PipelineStage(StrEnum):
    OBSERVATION = "observation"
    EVIDENCE = "evidence"
    HYPOTHESIS = "hypothesis"
    VALIDATION = "validation"
    RISK_ASSESSMENT = "risk_assessment"
    DECISION = "decision"
    EXECUTION = "execution"
    OUTCOME = "outcome"
    AUDIT = "audit"
    LEARNING = "learning"


ValidationStatus = Literal["passed", "failed", "inconclusive", "not_run"]
ExecutionStatus = Literal["preview", "blocked", "executed", "not_requested"]


class ObservationStage(BaseModel):
    """Raw signals — observation is not proof."""

    stage: Literal["observation"] = "observation"
    observation_id: str
    timestamp_utc: str
    source: str
    symptom: str = ""
    raw_signals: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class EvidenceStage(BaseModel):
    """Structured evidence bundle with explicit tier."""

    stage: Literal["evidence"] = "evidence"
    bundle: EvidenceBundle
    tier_summary: str = ""
    limitations: list[str] = Field(default_factory=list)


class HypothesisStage(BaseModel):
    """Competing explanation — correlation is not causation."""

    stage: Literal["hypothesis"] = "hypothesis"
    hypothesis: Hypothesis
    alternatives: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ValidationAttempt(BaseModel):
    name: str
    status: Literal["passed", "failed", "skipped", "inconclusive"] = "inconclusive"
    detail: str = ""


class ValidationStage(BaseModel):
    """Proof envelope results — confidence is not certainty."""

    stage: Literal["validation"] = "validation"
    validation_id: str
    timestamp_utc: str
    status: ValidationStatus = "not_run"
    proof_level: str = "observed"
    attempts: list[ValidationAttempt] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RiskAssessmentStage(BaseModel):
    """Ordinal risk framing for governance review."""

    stage: Literal["risk_assessment"] = "risk_assessment"
    assessment_id: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    user_impact: str = ""
    not_evidence_of: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DecisionStage(BaseModel):
    """Recommended action with human-review flags."""

    stage: Literal["decision"] = "decision"
    decision: Decision
    policy: PolicyEvaluation | None = None
    limitations: list[str] = Field(default_factory=list)


class ExecutionStage(BaseModel):
    """Preview-first execution record — registry changes require confirmation."""

    stage: Literal["execution"] = "execution"
    execution_id: str
    timestamp_utc: str
    action_id: str = ""
    dry_run: bool = True
    status: ExecutionStatus = "preview"
    registry_modified: bool = False
    confirmation_token: str = ""
    policy_outcome: str = "PREVIEW_ONLY"
    planned_changes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def registry_requires_confirmation(self) -> ExecutionStage:
        if self.registry_modified and not self.confirmation_token:
            msg = "registry_modified requires explicit confirmation_token"
            raise ValueError(msg)
        if self.registry_modified and self.dry_run:
            msg = "registry_modified cannot be set when dry_run is true"
            raise ValueError(msg)
        return self


class OutcomeStage(BaseModel):
    """Recorded result after decision/execution."""

    stage: Literal["outcome"] = "outcome"
    outcome: IncidentOutcome | None = None
    resolution_summary: str = ""
    limitations: list[str] = Field(default_factory=list)


class AuditStage(BaseModel):
    """Immutable audit trail references."""

    stage: Literal["audit"] = "audit"
    records: list[AuditRecord] = Field(default_factory=list)
    chain_verified: bool | None = None
    limitations: list[str] = Field(default_factory=list)


class LearningStage(BaseModel):
    """Continuous improvement signals."""

    stage: Literal["learning"] = "learning"
    records: list[LearningRecord] = Field(default_factory=list)
    recommended_controls: list[str] = Field(default_factory=list)
    recommended_tests: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class EvidenceCase(BaseModel):
    """
    End-to-end evidence case tracing:
    Observation → Evidence → Hypothesis → Validation → Risk Assessment
    → Decision → Execution → Outcome → Audit → Learning
    """

    case_id: str
    schema_version: str = EVIDENCE_CASE_SCHEMA_VERSION
    title: str
    created_at: str
    fixture_source: str = ""
    observation: ObservationStage
    evidence: EvidenceStage
    hypothesis: HypothesisStage
    validation: ValidationStage
    risk_assessment: RiskAssessmentStage
    decision: DecisionStage
    execution: ExecutionStage
    outcome: OutcomeStage
    audit: AuditStage
    learning: LearningStage
    epistemic_notice: str = (
        "Observation ≠ Proof · Correlation ≠ Causation · "
        "Confidence ≠ Certainty · Policy Permission ≠ Safety Guarantee"
    )
    limitations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def stage_names(self) -> list[str]:
        return [s.value for s in PipelineStage]

"""Senior-grade technology risk assurance workflow.

This module turns an incident-level risk decision into a reviewable assurance
artifact.  It deliberately separates evidence, control performance, management
acceptance, remediation, and the final assurance conclusion so that a reviewer
can see *why* a conclusion was reached and which conditions still block closure.

The model is governance-oriented rather than regulatory attestation.  It is
suitable for portfolio demonstrations, internal control analytics, and decision
support where human accountability must remain explicit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, Field, model_validator


class AssuranceConclusion(StrEnum):
    EFFECTIVE = "effective"
    EFFECTIVE_WITH_OBSERVATIONS = "effective_with_observations"
    INEFFECTIVE = "ineffective"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ExceptionStatus(StrEnum):
    OPEN = "open"
    IN_REMEDIATION = "in_remediation"
    PENDING_VALIDATION = "pending_validation"
    CLOSED = "closed"
    RISK_ACCEPTED = "risk_accepted"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_RISK_WEIGHT: dict[RiskLevel, int] = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class ControlException(BaseModel):
    """A control exception with an accountable owner and closure conditions."""

    exception_id: str
    control_id: str
    title: str
    risk_level: RiskLevel
    owner: str
    status: ExceptionStatus = ExceptionStatus.OPEN
    remediation_due_at: str | None = None
    remediation_plan: str = ""
    validation_evidence_ids: list[str] = Field(default_factory=list)
    management_acceptance_id: str | None = None

    @property
    def blocks_assurance(self) -> bool:
        return self.status not in {ExceptionStatus.CLOSED, ExceptionStatus.RISK_ACCEPTED}


class ManagementSignOff(BaseModel):
    """Explicit management accountability for the residual-risk decision."""

    signoff_id: str
    signer_id: str
    signer_role: str
    accepted_residual_risk: RiskLevel
    rationale: str
    signed_at: str
    scope: str = "incident"


class AssuranceInput(BaseModel):
    """Normalized facts consumed by the deterministic assurance engine."""

    incident_id: str
    inherent_risk: RiskLevel
    residual_risk: RiskLevel
    evidence_sufficient: bool
    control_effectiveness: float = Field(ge=0.0, le=1.0)
    control_failures: int = Field(ge=0)
    critical_control_failures: int = Field(ge=0)
    human_review_completed: bool = False
    remediation_verified: bool = False
    exceptions: list[ControlException] = Field(default_factory=list)
    management_signoff: ManagementSignOff | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_control_failure_counts(self) -> "AssuranceInput":
        if self.critical_control_failures > self.control_failures:
            raise ValueError("critical_control_failures cannot exceed control_failures")
        return self


class AssuranceDecision(BaseModel):
    """Deterministic assurance conclusion plus the conditions behind it."""

    schema_version: str = "senior_assurance_decision.v1"
    incident_id: str
    conclusion: AssuranceConclusion
    residual_risk: RiskLevel
    closure_allowed: bool
    management_signoff_required: bool
    open_exception_ids: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    decided_at: str


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _open_exceptions(exceptions: Iterable[ControlException]) -> list[ControlException]:
    return [item for item in exceptions if item.blocks_assurance]


def _signoff_covers_residual_risk(
    residual_risk: RiskLevel,
    signoff: ManagementSignOff | None,
) -> bool:
    if signoff is None:
        return False
    return _RISK_WEIGHT[signoff.accepted_residual_risk] >= _RISK_WEIGHT[residual_risk]


def assess_assurance(data: AssuranceInput) -> AssuranceDecision:
    """Produce a senior-style assurance decision from normalized risk facts.

    Decision hierarchy:
    1. Insufficient evidence always blocks closure.
    2. Critical control failure forces an ineffective conclusion.
    3. Open high/critical exceptions block closure until remediated or accepted.
    4. High/critical residual risk requires explicit management sign-off.
    5. Effective controls with no unresolved blockers can be closed.

    No branch in this function grants execution authority.  Remediation remains
    subject to the repository's existing human-review and policy gates.
    """

    rationale: list[str] = []
    open_items = _open_exceptions(data.exceptions)
    open_ids = [item.exception_id for item in open_items]
    signoff_required = data.residual_risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    signoff_ok = _signoff_covers_residual_risk(data.residual_risk, data.management_signoff)

    if not data.evidence_sufficient:
        rationale.append("Evidence is insufficient to support a reliable assurance conclusion.")
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.INSUFFICIENT_EVIDENCE,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=signoff_required,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    if data.critical_control_failures > 0:
        rationale.append(
            f"{data.critical_control_failures} critical control failure(s) remain in scope."
        )
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.INEFFECTIVE,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=signoff_required,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    unresolved_material = [
        item
        for item in open_items
        if item.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    ]
    if unresolved_material:
        rationale.append(
            "Material control exceptions remain unresolved: "
            + ", ".join(item.exception_id for item in unresolved_material)
            + "."
        )
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.INEFFECTIVE,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=signoff_required,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    if not data.human_review_completed:
        rationale.append("Required human review has not been completed.")
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=signoff_required,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    if data.control_failures > 0 and not data.remediation_verified:
        rationale.append("Control failures exist and remediation has not been independently verified.")
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=signoff_required,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    if signoff_required and not signoff_ok:
        rationale.append(
            f"Residual risk is {data.residual_risk.value}; adequate management sign-off is required."
        )
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=True,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    if data.control_effectiveness < 0.75:
        rationale.append(
            f"Control effectiveness is {data.control_effectiveness:.0%}, below the 75% closure threshold."
        )
        return AssuranceDecision(
            incident_id=data.incident_id,
            conclusion=AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS,
            residual_risk=data.residual_risk,
            closure_allowed=False,
            management_signoff_required=signoff_required,
            open_exception_ids=open_ids,
            rationale=rationale,
            limitations=list(dict.fromkeys(data.limitations)),
            decided_at=_now(),
        )

    if open_items:
        rationale.append(
            "Only low/medium non-material exceptions remain; closure is allowed with observations."
        )
        conclusion = AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS
    else:
        rationale.append("Evidence, control performance, review, and residual-risk gates are satisfied.")
        conclusion = AssuranceConclusion.EFFECTIVE

    return AssuranceDecision(
        incident_id=data.incident_id,
        conclusion=conclusion,
        residual_risk=data.residual_risk,
        closure_allowed=True,
        management_signoff_required=signoff_required,
        open_exception_ids=open_ids,
        rationale=rationale,
        limitations=list(dict.fromkeys(data.limitations)),
        decided_at=_now(),
    )

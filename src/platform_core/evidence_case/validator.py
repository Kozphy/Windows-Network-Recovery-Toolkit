"""Validate Evidence Case structure, policy gates, and safety contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from .models import EvidenceCase, ExecutionStage, PipelineStage


@dataclass
class ValidationIssue:
    code: str
    message: str
    stage: str = ""


@dataclass
class EvidenceCaseValidationResult:
    valid: bool
    case_id: str = ""
    issues: list[ValidationIssue] = field(default_factory=list)
    stages_present: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "case_id": self.case_id,
            "stages_present": self.stages_present,
            "issues": [{"code": i.code, "message": i.message, "stage": i.stage} for i in self.issues],
        }


def validate_evidence_case(case: EvidenceCase | dict[str, Any]) -> EvidenceCaseValidationResult:
    """Validate case model, pipeline completeness, and registry safety."""
    issues: list[ValidationIssue] = []

    try:
        model = case if isinstance(case, EvidenceCase) else EvidenceCase.model_validate(case)
    except ValidationError as exc:
        return EvidenceCaseValidationResult(
            valid=False,
            issues=[ValidationIssue(code="schema_invalid", message=str(exc))],
        )

    stages_present = [
        PipelineStage.OBSERVATION.value,
        PipelineStage.EVIDENCE.value,
        PipelineStage.HYPOTHESIS.value,
        PipelineStage.VALIDATION.value,
        PipelineStage.RISK_ASSESSMENT.value,
        PipelineStage.DECISION.value,
        PipelineStage.EXECUTION.value,
        PipelineStage.OUTCOME.value,
        PipelineStage.AUDIT.value,
        PipelineStage.LEARNING.value,
    ]

    if not model.observation.raw_signals and not model.observation.symptom:
        issues.append(
            ValidationIssue(
                code="empty_observation",
                message="Observation must include symptom or raw_signals.",
                stage="observation",
            )
        )

    if not model.evidence.bundle.items:
        issues.append(
            ValidationIssue(
                code="empty_evidence",
                message="Evidence bundle must contain at least one item.",
                stage="evidence",
            )
        )

    conf = model.hypothesis.hypothesis.confidence
    if not 0.0 <= conf <= 1.0:
        issues.append(
            ValidationIssue(
                code="confidence_out_of_range",
                message=f"Hypothesis confidence {conf} must be between 0.0 and 1.0.",
                stage="hypothesis",
            )
        )

    risk_conf = model.risk_assessment.confidence
    if not 0.0 <= risk_conf <= 1.0:
        issues.append(
            ValidationIssue(
                code="risk_confidence_out_of_range",
                message=f"Risk confidence {risk_conf} must be between 0.0 and 1.0.",
                stage="risk_assessment",
            )
        )

    issues.extend(_validate_execution_safety(model.execution))

    if model.execution.registry_modified and model.decision.policy:
        policy = model.decision.policy
        if policy.outcome in {"BLOCK", "PREVIEW_ONLY"}:
            issues.append(
                ValidationIssue(
                    code="registry_without_policy_allow",
                    message="Registry modification blocked — policy outcome does not allow execution.",
                    stage="execution",
                )
            )

    if model.epistemic_notice and "Observation" not in model.epistemic_notice:
        issues.append(
            ValidationIssue(
                code="missing_epistemic_notice",
                message="Epistemic notice should state Observation ≠ Proof.",
                stage="audit",
            )
        )

    return EvidenceCaseValidationResult(
        valid=not issues,
        case_id=model.case_id,
        issues=issues,
        stages_present=stages_present,
    )


def _validate_execution_safety(execution: ExecutionStage) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if execution.registry_modified:
        if execution.dry_run:
            issues.append(
                ValidationIssue(
                    code="registry_modified_during_dry_run",
                    message="registry_modified cannot be true when dry_run is true.",
                    stage="execution",
                )
            )
        if not execution.confirmation_token:
            issues.append(
                ValidationIssue(
                    code="registry_missing_confirmation",
                    message="registry_modified requires explicit confirmation_token.",
                    stage="execution",
                )
            )
        allowed_tokens = {"DISABLE_WININET_PROXY", "RESTORE_WININET_PROXY_FROM_LKG"}
        if execution.confirmation_token not in allowed_tokens:
            issues.append(
                ValidationIssue(
                    code="registry_invalid_confirmation",
                    message=f"confirmation_token must be one of {sorted(allowed_tokens)}.",
                    stage="execution",
                )
            )

    if execution.status == "executed" and execution.dry_run:
        issues.append(
            ValidationIssue(
                code="executed_while_dry_run",
                message="status=executed is inconsistent with dry_run=true.",
                stage="execution",
            )
        )

    return issues

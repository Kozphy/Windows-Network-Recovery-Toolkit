"""Adapter from incident fixtures to senior assurance governance artifacts.

This module bridges the existing proof/risk/control pipeline with the deterministic
senior assurance engine.  It keeps the assurance layer derived from auditable
facts already produced by the platform instead of requiring a second manual
input model.
"""

from __future__ import annotations

from typing import Any

from src.platform_core.governance.senior_assurance import (
    AssuranceDecision,
    AssuranceInput,
    ControlException,
    ExceptionStatus,
    ManagementSignOff,
    RiskLevel,
    assess_assurance,
)
from src.platform_core.risk.control_test_mature import MatureTestResult, run_mature_control_tests
from src.platform_core.risk.risk_rating import RiskRating


_RISK_ALIASES = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}


def _risk_level(value: str | None, *, default: RiskLevel = RiskLevel.MEDIUM) -> RiskLevel:
    return _RISK_ALIASES.get(str(value or "").strip().lower(), default)


def _exception_level(result: MatureTestResult) -> RiskLevel:
    if result == MatureTestResult.FAIL:
        return RiskLevel.HIGH
    if result == MatureTestResult.PARTIAL:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _exception_status(fixture: dict[str, Any], control_id: str) -> ExceptionStatus:
    raw = (fixture.get("control_exception_status") or {}).get(control_id)
    if raw:
        try:
            return ExceptionStatus(str(raw).lower())
        except ValueError:
            pass
    return ExceptionStatus.OPEN


def build_control_exceptions(fixture: dict[str, Any]) -> list[ControlException]:
    """Create an exception register from failed/partial mature control tests."""
    records: list[ControlException] = []
    remediation = fixture.get("remediation") or {}
    due_dates = fixture.get("remediation_due_at") or {}
    validation = fixture.get("validation_evidence") or {}
    acceptance = fixture.get("management_acceptance") or {}

    for test in run_mature_control_tests(fixture):
        if test.test_result not in {MatureTestResult.FAIL, MatureTestResult.PARTIAL}:
            continue
        control_id = test.control_id
        records.append(
            ControlException(
                exception_id=f"EXC-{control_id}",
                control_id=control_id,
                title=f"{test.control_name}: {test.test_result.value}",
                risk_level=_exception_level(test.test_result),
                owner=test.remediation_owner,
                status=_exception_status(fixture, control_id),
                remediation_due_at=due_dates.get(control_id),
                remediation_plan=str(remediation.get(control_id) or ""),
                validation_evidence_ids=list(validation.get(control_id) or []),
                management_acceptance_id=acceptance.get(control_id),
            )
        )
    return records


def _management_signoff(fixture: dict[str, Any]) -> ManagementSignOff | None:
    raw = fixture.get("management_signoff") or {}
    if not raw:
        return None
    required = {"signoff_id", "signer_id", "signer_role", "accepted_residual_risk", "rationale", "signed_at"}
    if not required.issubset(raw):
        return None
    try:
        return ManagementSignOff(
            signoff_id=str(raw["signoff_id"]),
            signer_id=str(raw["signer_id"]),
            signer_role=str(raw["signer_role"]),
            accepted_residual_risk=_risk_level(str(raw["accepted_residual_risk"])),
            rationale=str(raw["rationale"]),
            signed_at=str(raw["signed_at"]),
            scope=str(raw.get("scope") or "incident"),
        )
    except (TypeError, ValueError):
        return None


def build_assurance_decision(
    fixture: dict[str, Any],
    rating: RiskRating,
) -> tuple[AssuranceDecision, list[ControlException]]:
    """Derive a senior assurance conclusion from platform-native facts."""
    mature = run_mature_control_tests(fixture)
    exceptions = build_control_exceptions(fixture)
    tested = [t for t in mature if t.test_result != MatureTestResult.NOT_TESTED]
    failures = [t for t in tested if t.test_result in {MatureTestResult.FAIL, MatureTestResult.PARTIAL}]
    critical_failures = [
        t for t in tested
        if t.test_result == MatureTestResult.FAIL and "critical" in t.residual_risk.lower()
    ]

    proof_status = str(((fixture.get("proof") or {}).get("conclusion") or {}).get("status") or "not_run")
    evidence_sufficient = proof_status in {"supported", "failed"}
    evidence_sufficient = bool(fixture.get("evidence_sufficient", evidence_sufficient))

    review = fixture.get("human_review") or {}
    human_review_completed = bool(
        fixture.get("human_review_completed", review.get("completed", False))
    )
    remediation_verified = bool(
        fixture.get("remediation_verified", (fixture.get("verification") or {}).get("verified", False))
    )

    limitations = list(rating.limitations)
    if not tested:
        limitations.append("No mature control test was in scope for this incident fixture.")

    assurance_input = AssuranceInput(
        incident_id=str(fixture.get("case_id") or fixture.get("incident_id") or "unassigned"),
        inherent_risk=_risk_level(rating.inherent_level),
        residual_risk=_risk_level(rating.residual_level),
        evidence_sufficient=evidence_sufficient,
        control_effectiveness=rating.control_effectiveness,
        control_failures=len(failures),
        critical_control_failures=len(critical_failures),
        human_review_completed=human_review_completed,
        remediation_verified=remediation_verified,
        exceptions=exceptions,
        management_signoff=_management_signoff(fixture),
        limitations=limitations,
    )
    return assess_assurance(assurance_input), exceptions

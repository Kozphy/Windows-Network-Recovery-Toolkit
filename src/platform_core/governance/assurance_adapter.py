"""Adapter from incident fixtures to senior assurance governance artifacts.

This module bridges the existing proof/risk/control pipeline with the deterministic
senior assurance engine. It keeps assurance derived from auditable platform facts
and treats missing review/verification evidence conservatively.
"""

from __future__ import annotations

from typing import Any

from src.platform_core.governance.proof_tier import ProofTier, resolve_proof_tier
from src.platform_core.governance.senior_assurance import (
    AssuranceDecision,
    AssuranceInput,
    ControlException,
    ExceptionStatus,
    ManagementSignOff,
    RiskLevel,
    assess_assurance,
)
from src.platform_core.risk.control_test_mature import (
    ControlTestMatureRecord,
    MatureTestResult,
    run_mature_control_tests,
)
from src.platform_core.risk.risk_rating import RiskRating


_RISK_ALIASES = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}


def _risk_level(value: str | RiskLevel | None, *, default: RiskLevel = RiskLevel.MEDIUM) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    return _RISK_ALIASES.get(str(value or "").strip().lower(), default)


def _config(fixture: dict[str, Any]) -> dict[str, Any]:
    value = fixture.get("assurance") or {}
    return value if isinstance(value, dict) else {}


def _exception_level(result: MatureTestResult) -> RiskLevel:
    if result == MatureTestResult.FAIL:
        return RiskLevel.HIGH
    if result == MatureTestResult.PARTIAL:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _exception_overrides(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in _config(fixture).get("exceptions") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("control_id") or item.get("exception_id") or "").strip()
        if key:
            result[key] = item
    return result


def _exception_status(fixture: dict[str, Any], control_id: str, override: dict[str, Any]) -> ExceptionStatus:
    raw = override.get("status")
    if raw is None:
        raw = (fixture.get("control_exception_status") or {}).get(control_id)
    try:
        return ExceptionStatus(str(raw or "open").lower())
    except ValueError:
        return ExceptionStatus.OPEN


def build_control_exceptions(
    fixture: dict[str, Any],
    mature_tests: list[ControlTestMatureRecord] | None = None,
) -> list[ControlException]:
    """Create an exception register from failed/partial mature control tests.

    A claimed CLOSED exception without validation evidence is downgraded to
    PENDING_VALIDATION. This prevents metadata alone from asserting closure.
    """
    records: list[ControlException] = []
    remediation = fixture.get("remediation") or {}
    due_dates = fixture.get("remediation_due_at") or {}
    validation = fixture.get("validation_evidence") or {}
    acceptance = fixture.get("management_acceptance") or {}
    overrides = _exception_overrides(fixture)

    for test in mature_tests or run_mature_control_tests(fixture):
        if test.test_result not in {MatureTestResult.FAIL, MatureTestResult.PARTIAL}:
            continue
        control_id = test.control_id
        override = overrides.get(control_id, {})
        evidence_ids = list(
            override.get("validation_evidence_ids")
            or validation.get(control_id)
            or []
        )
        status = _exception_status(fixture, control_id, override)
        if status == ExceptionStatus.CLOSED and not evidence_ids:
            status = ExceptionStatus.PENDING_VALIDATION

        records.append(
            ControlException(
                exception_id=str(override.get("exception_id") or f"EXC-{control_id}"),
                control_id=control_id,
                title=str(override.get("title") or f"{test.control_name}: {test.test_result.value}"),
                risk_level=_risk_level(
                    override.get("risk_level"),
                    default=_exception_level(test.test_result),
                ),
                owner=str(override.get("owner") or test.remediation_owner or "unassigned"),
                status=status,
                remediation_due_at=override.get("remediation_due_at") or due_dates.get(control_id),
                remediation_plan=str(
                    override.get("remediation_plan") or remediation.get(control_id) or ""
                ),
                validation_evidence_ids=[str(item) for item in evidence_ids],
                management_acceptance_id=(
                    override.get("management_acceptance_id") or acceptance.get(control_id)
                ),
            )
        )
    return records


def _management_signoff(fixture: dict[str, Any]) -> ManagementSignOff | None:
    raw = _config(fixture).get("management_signoff") or fixture.get("management_signoff") or {}
    if not isinstance(raw, dict) or not raw:
        return None
    required = {
        "signoff_id",
        "signer_id",
        "signer_role",
        "accepted_residual_risk",
        "rationale",
        "signed_at",
    }
    if any(not raw.get(key) for key in required):
        return None
    return ManagementSignOff(
        signoff_id=str(raw["signoff_id"]),
        signer_id=str(raw["signer_id"]),
        signer_role=str(raw["signer_role"]),
        accepted_residual_risk=_risk_level(raw["accepted_residual_risk"]),
        rationale=str(raw["rationale"]),
        signed_at=str(raw["signed_at"]),
        scope=str(raw.get("scope") or "incident"),
    )


def _evidence_sufficient(fixture: dict[str, Any]) -> bool:
    config = _config(fixture)
    if "evidence_sufficient" in config:
        return bool(config["evidence_sufficient"])
    if "evidence_sufficient" in fixture:
        return bool(fixture["evidence_sufficient"])

    proof_status = str(
        ((fixture.get("proof") or {}).get("conclusion") or {}).get("status") or "not_run"
    )
    proof = resolve_proof_tier(fixture)
    return (
        proof.proof_tier != ProofTier.T0_OBSERVATION_ONLY
        and proof_status not in {"not_run", "inconclusive", ""}
    )


def _review_completed(fixture: dict[str, Any]) -> bool:
    config = _config(fixture)
    review = fixture.get("human_review") or {}
    if "human_review_completed" in config:
        return bool(config["human_review_completed"])
    return bool(fixture.get("human_review_completed", review.get("completed", False)))


def _remediation_verified(fixture: dict[str, Any], exceptions: list[ControlException]) -> bool:
    config = _config(fixture)
    if "remediation_verified" in config:
        return bool(config["remediation_verified"])
    if "remediation_verified" in fixture:
        return bool(fixture["remediation_verified"])
    verification = fixture.get("verification") or {}
    if "verified" in verification:
        return bool(verification["verified"])

    unresolved = [
        item
        for item in exceptions
        if item.status not in {ExceptionStatus.CLOSED, ExceptionStatus.RISK_ACCEPTED}
    ]
    if unresolved:
        return False
    closed = [item for item in exceptions if item.status == ExceptionStatus.CLOSED]
    return all(item.validation_evidence_ids for item in closed)


def build_assurance_decision(
    fixture: dict[str, Any],
    rating: RiskRating,
    *,
    incident_id: str | None = None,
) -> tuple[AssuranceDecision, list[ControlException]]:
    """Derive a senior assurance conclusion from platform-native facts."""
    mature = run_mature_control_tests(fixture)
    exceptions = build_control_exceptions(fixture, mature)
    tested = [t for t in mature if t.test_result != MatureTestResult.NOT_TESTED]
    failures = [t for t in tested if t.test_result in {MatureTestResult.FAIL, MatureTestResult.PARTIAL}]

    config = _config(fixture)
    critical_control_ids = {
        str(value)
        for value in (
            config.get("critical_control_ids")
            or fixture.get("critical_control_ids")
            or []
        )
    }
    critical_failures = [
        t
        for t in tested
        if t.test_result == MatureTestResult.FAIL and t.control_id in critical_control_ids
    ]

    limitations = list(rating.limitations)
    if not tested:
        limitations.append("No mature control test was in scope for this incident fixture.")

    assurance_input = AssuranceInput(
        incident_id=str(
            incident_id
            or fixture.get("case_id")
            or fixture.get("incident_id")
            or "unassigned"
        ),
        inherent_risk=_risk_level(rating.inherent_level),
        residual_risk=_risk_level(rating.residual_level),
        evidence_sufficient=_evidence_sufficient(fixture),
        control_effectiveness=rating.control_effectiveness,
        control_failures=len(failures),
        critical_control_failures=len(critical_failures),
        human_review_completed=_review_completed(fixture),
        remediation_verified=_remediation_verified(fixture, exceptions),
        exceptions=exceptions,
        management_signoff=_management_signoff(fixture),
        limitations=list(dict.fromkeys(limitations)),
    )
    return assess_assurance(assurance_input), exceptions

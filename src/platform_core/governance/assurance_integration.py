"""Integration helpers that connect incident risk assessment to senior assurance.

The senior-assurance engine deliberately operates on normalized facts.  This
module is the adapter between existing fixture/control-test outputs and that
engine, keeping assumptions explicit and conservative.
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
from src.platform_core.risk.control_test import ControlTest, ControlTestResult
from src.platform_core.risk.control_test_mature import (
    ControlTestMatureRecord,
    MatureTestResult,
)
from src.platform_core.risk.risk_rating import RiskRating


_RISK_LEVELS = {item.value: item for item in RiskLevel}


def _risk_level(value: str | RiskLevel | None, default: RiskLevel = RiskLevel.MEDIUM) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    normalized = str(value or "").strip().lower()
    return _RISK_LEVELS.get(normalized, default)


def _assurance_config(fixture: dict[str, Any]) -> dict[str, Any]:
    value = fixture.get("assurance") or {}
    return value if isinstance(value, dict) else {}


def _exception_status(value: str | None) -> ExceptionStatus:
    normalized = str(value or "").strip().lower()
    for item in ExceptionStatus:
        if item.value == normalized:
            return item
    return ExceptionStatus.OPEN


def _explicit_exception_overrides(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    config = _assurance_config(fixture)
    result: dict[str, dict[str, Any]] = {}
    for item in config.get("exceptions") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("control_id") or item.get("exception_id") or "").strip()
        if key:
            result[key] = item
    return result


def _exceptions_from_mature_tests(
    fixture: dict[str, Any],
    mature_tests: list[ControlTestMatureRecord],
) -> list[ControlException]:
    """Convert FAIL/PARTIAL mature tests into accountable control exceptions.

    PASS and NOT_TESTED are not exceptions. PARTIAL defaults to medium risk;
    FAIL defaults to high risk. Explicit fixture assurance metadata may override
    owner, status, due date, risk, remediation plan, and validation linkage.
    """
    overrides = _explicit_exception_overrides(fixture)
    exceptions: list[ControlException] = []
    for test in mature_tests:
        if test.test_result not in {MatureTestResult.FAIL, MatureTestResult.PARTIAL}:
            continue

        override = overrides.get(test.control_id, {})
        default_risk = RiskLevel.HIGH if test.test_result == MatureTestResult.FAIL else RiskLevel.MEDIUM
        status = _exception_status(override.get("status"))
        validation_ids = [str(v) for v in override.get("validation_evidence_ids") or [] if str(v).strip()]
        if status == ExceptionStatus.CLOSED and not validation_ids:
            # A closed exception without verification evidence is downgraded to
            # pending validation so closure cannot be asserted by metadata alone.
            status = ExceptionStatus.PENDING_VALIDATION

        exceptions.append(
            ControlException(
                exception_id=str(override.get("exception_id") or f"EXC-{test.control_id}"),
                control_id=test.control_id,
                title=str(override.get("title") or f"{test.control_name}: {test.test_result.value}"),
                risk_level=_risk_level(override.get("risk_level"), default_risk),
                owner=str(override.get("owner") or test.remediation_owner or "unassigned"),
                status=status,
                remediation_due_at=override.get("remediation_due_at"),
                remediation_plan=str(override.get("remediation_plan") or ""),
                validation_evidence_ids=validation_ids,
                management_acceptance_id=override.get("management_acceptance_id"),
            )
        )
    return exceptions


def _management_signoff(fixture: dict[str, Any]) -> ManagementSignOff | None:
    raw = _assurance_config(fixture).get("management_signoff")
    if not isinstance(raw, dict) or not raw:
        return None
    required = {"signoff_id", "signer_id", "signer_role", "accepted_residual_risk", "rationale", "signed_at"}
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
    config = _assurance_config(fixture)
    if "evidence_sufficient" in config:
        return bool(config["evidence_sufficient"])

    proof = resolve_proof_tier(fixture)
    conclusion = ((fixture.get("proof") or {}).get("conclusion") or {}).get("status")
    return proof.proof_tier != ProofTier.T0_OBSERVATION_ONLY and conclusion not in {
        None,
        "",
        "not_run",
        "inconclusive",
    }


def _human_review_completed(fixture: dict[str, Any]) -> bool:
    config = _assurance_config(fixture)
    # Never infer a completed review merely because policy requires one.
    return bool(config.get("human_review_completed", False))


def _remediation_verified(
    fixture: dict[str, Any],
    exceptions: list[ControlException],
) -> bool:
    config = _assurance_config(fixture)
    if "remediation_verified" in config:
        return bool(config["remediation_verified"])
    material = [item for item in exceptions if item.status not in {ExceptionStatus.CLOSED, ExceptionStatus.RISK_ACCEPTED}]
    if material:
        return False
    closed = [item for item in exceptions if item.status == ExceptionStatus.CLOSED]
    return all(item.validation_evidence_ids for item in closed)


def build_assurance_input(
    fixture: dict[str, Any],
    *,
    rating: RiskRating,
    control_tests: list[ControlTest],
    mature_tests: list[ControlTestMatureRecord],
    incident_id: str,
) -> AssuranceInput:
    """Normalize existing assessment outputs into a deterministic AssuranceInput."""
    exceptions = _exceptions_from_mature_tests(fixture, mature_tests)
    failures = sum(1 for test in control_tests if test.result == ControlTestResult.FAIL)
    critical_ids = set(str(v) for v in (_assurance_config(fixture).get("critical_control_ids") or []))
    critical_failures = sum(
        1
        for test in control_tests
        if test.result == ControlTestResult.FAIL and test.control_id in critical_ids
    )

    limitations = list(rating.limitations)
    for test in mature_tests:
        if test.test_result in {MatureTestResult.PARTIAL, MatureTestResult.NOT_TESTED} and test.limitation:
            limitations.append(test.limitation)

    return AssuranceInput(
        incident_id=incident_id,
        inherent_risk=_risk_level(rating.inherent_level),
        residual_risk=_risk_level(rating.residual_level),
        evidence_sufficient=_evidence_sufficient(fixture),
        control_effectiveness=rating.control_effectiveness,
        control_failures=failures,
        critical_control_failures=critical_failures,
        human_review_completed=_human_review_completed(fixture),
        remediation_verified=_remediation_verified(fixture, exceptions),
        exceptions=exceptions,
        management_signoff=_management_signoff(fixture),
        limitations=list(dict.fromkeys(limitations)),
    )


def assess_fixture_assurance(
    fixture: dict[str, Any],
    *,
    rating: RiskRating,
    control_tests: list[ControlTest],
    mature_tests: list[ControlTestMatureRecord],
    incident_id: str,
) -> AssuranceDecision:
    """Assess assurance for an existing technology-risk fixture."""
    normalized = build_assurance_input(
        fixture,
        rating=rating,
        control_tests=control_tests,
        mature_tests=mature_tests,
        incident_id=incident_id,
    )
    return assess_assurance(normalized)


def assurance_register(
    fixture: dict[str, Any],
    *,
    mature_tests: list[ControlTestMatureRecord],
) -> list[dict[str, Any]]:
    """Return a report-friendly exception register."""
    return [item.model_dump(mode="json") for item in _exceptions_from_mature_tests(fixture, mature_tests)]

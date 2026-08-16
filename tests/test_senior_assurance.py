from __future__ import annotations

from src.platform_core.governance.senior_assurance import (
    AssuranceConclusion,
    AssuranceInput,
    ControlException,
    ExceptionStatus,
    ManagementSignOff,
    RiskLevel,
    assess_assurance,
)


def _base(**overrides):
    data = {
        "incident_id": "INC-ASSURANCE-001",
        "inherent_risk": RiskLevel.HIGH,
        "residual_risk": RiskLevel.MEDIUM,
        "evidence_sufficient": True,
        "control_effectiveness": 0.90,
        "control_failures": 0,
        "critical_control_failures": 0,
        "human_review_completed": True,
        "remediation_verified": True,
    }
    data.update(overrides)
    return AssuranceInput(**data)


def test_insufficient_evidence_blocks_closure() -> None:
    decision = assess_assurance(_base(evidence_sufficient=False))
    assert decision.conclusion == AssuranceConclusion.INSUFFICIENT_EVIDENCE
    assert decision.closure_allowed is False


def test_critical_control_failure_is_ineffective() -> None:
    decision = assess_assurance(
        _base(control_failures=1, critical_control_failures=1)
    )
    assert decision.conclusion == AssuranceConclusion.INEFFECTIVE
    assert decision.closure_allowed is False


def test_material_open_exception_blocks_closure() -> None:
    exception = ControlException(
        exception_id="EXC-001",
        control_id="CTRL-EPR-001",
        title="Dead localhost proxy remains configured",
        risk_level=RiskLevel.HIGH,
        owner="endpoint-operations",
        status=ExceptionStatus.IN_REMEDIATION,
        remediation_plan="Remove stale proxy and verify direct path.",
    )
    decision = assess_assurance(_base(exceptions=[exception]))
    assert decision.conclusion == AssuranceConclusion.INEFFECTIVE
    assert decision.open_exception_ids == ["EXC-001"]


def test_high_residual_risk_requires_signoff() -> None:
    decision = assess_assurance(_base(residual_risk=RiskLevel.HIGH))
    assert decision.conclusion == AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS
    assert decision.management_signoff_required is True
    assert decision.closure_allowed is False


def test_high_residual_risk_closes_with_adequate_signoff() -> None:
    signoff = ManagementSignOff(
        signoff_id="SO-001",
        signer_id="mgr-001",
        signer_role="Technology Risk Owner",
        accepted_residual_risk=RiskLevel.HIGH,
        rationale="Compensating monitoring remains active until permanent remediation.",
        signed_at="2026-08-16T10:00:00Z",
    )
    decision = assess_assurance(
        _base(residual_risk=RiskLevel.HIGH, management_signoff=signoff)
    )
    assert decision.conclusion == AssuranceConclusion.EFFECTIVE
    assert decision.closure_allowed is True


def test_signoff_cannot_accept_risk_below_actual_residual_level() -> None:
    signoff = ManagementSignOff(
        signoff_id="SO-002",
        signer_id="mgr-002",
        signer_role="Control Owner",
        accepted_residual_risk=RiskLevel.MEDIUM,
        rationale="Accept medium risk.",
        signed_at="2026-08-16T10:00:00Z",
    )
    decision = assess_assurance(
        _base(residual_risk=RiskLevel.HIGH, management_signoff=signoff)
    )
    assert decision.closure_allowed is False
    assert decision.management_signoff_required is True


def test_failed_controls_require_verified_remediation() -> None:
    decision = assess_assurance(
        _base(control_failures=1, remediation_verified=False)
    )
    assert decision.conclusion == AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS
    assert decision.closure_allowed is False


def test_low_control_effectiveness_blocks_closure() -> None:
    decision = assess_assurance(_base(control_effectiveness=0.70))
    assert decision.conclusion == AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS
    assert decision.closure_allowed is False


def test_low_open_exception_allows_closure_with_observation() -> None:
    exception = ControlException(
        exception_id="EXC-LOW-001",
        control_id="CTRL-EPR-006",
        title="Monitoring interval improvement",
        risk_level=RiskLevel.LOW,
        owner="platform-operations",
        status=ExceptionStatus.OPEN,
    )
    decision = assess_assurance(_base(exceptions=[exception]))
    assert decision.conclusion == AssuranceConclusion.EFFECTIVE_WITH_OBSERVATIONS
    assert decision.closure_allowed is True


def test_closed_material_exception_does_not_block_closure() -> None:
    exception = ControlException(
        exception_id="EXC-CLOSED-001",
        control_id="CTRL-EPR-001",
        title="Dead proxy remediated",
        risk_level=RiskLevel.HIGH,
        owner="endpoint-operations",
        status=ExceptionStatus.CLOSED,
        validation_evidence_ids=["EV-VERIFY-001"],
    )
    decision = assess_assurance(_base(exceptions=[exception]))
    assert decision.conclusion == AssuranceConclusion.EFFECTIVE
    assert decision.closure_allowed is True


def test_critical_failure_count_cannot_exceed_total_failures() -> None:
    try:
        _base(control_failures=0, critical_control_failures=1)
    except ValueError as exc:
        assert "critical_control_failures" in str(exc)
    else:
        raise AssertionError("invalid failure counts must be rejected")

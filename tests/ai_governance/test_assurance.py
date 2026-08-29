from platform_core.ai_governance import (
    AIDecisionRecord,
    AIGovernanceAssuranceService,
    DataLineage,
    ModelVersion,
    PromptVersion,
    RiskRating,
)


def build_record(risk: RiskRating = RiskRating.HIGH) -> AIDecisionRecord:
    service = AIGovernanceAssuranceService()
    return AIDecisionRecord(
        decision_id="decision-001",
        use_case="endpoint-remediation",
        model=ModelVersion(provider="openai", model_name="example-model", version="2026-08"),
        prompt=PromptVersion.from_template("remediation", "v1", "Diagnose endpoint state"),
        lineage=[DataLineage(source_system="endpoint-agent", dataset_id="host-001")],
        input_hash="input-sha256",
        output_hash="output-sha256",
        rationale_summary="Proxy drift is supported by collected endpoint evidence.",
        risk_rating=risk,
        controls=service.baseline_controls(),
        action="repair_proxy_configuration",
        rollback_ref="rollback://host-001/proxy",
    )


def test_high_risk_decision_requires_human_approval() -> None:
    service = AIGovernanceAssuranceService()
    decision = service.evaluate(build_record())
    assert decision.allowed is False
    assert "human approval required" in decision.reasons


def test_approved_high_risk_decision_can_pass_gate() -> None:
    service = AIGovernanceAssuranceService()
    record = service.attach_approval(
        build_record(),
        approver="risk-owner@example.com",
        role="Technology Risk Owner",
        approved=True,
        rationale="Evidence and rollback plan reviewed.",
    )
    decision = service.evaluate(record)
    assert decision.allowed is True
    assert decision.reasons == ()


def test_failed_control_blocks_execution() -> None:
    service = AIGovernanceAssuranceService()
    record = build_record(RiskRating.MEDIUM)
    record.controls[0].passed = False
    decision = service.evaluate(record)
    assert decision.allowed is False
    assert any("AI-GOV-01" in reason for reason in decision.reasons)


def test_risk_score_boundaries() -> None:
    service = AIGovernanceAssuranceService()
    assert service.risk_from_score(0.20) == RiskRating.LOW
    assert service.risk_from_score(0.50) == RiskRating.MEDIUM
    assert service.risk_from_score(0.70) == RiskRating.HIGH
    assert service.risk_from_score(0.90) == RiskRating.CRITICAL

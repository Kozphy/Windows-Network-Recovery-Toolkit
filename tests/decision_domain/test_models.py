from __future__ import annotations

import pytest
from pydantic import ValidationError

from platform_core.decision_domain import (
    Decision,
    DecisionContext,
    DecisionDomain,
    DecisionEvidence,
    DecisionExplanation,
    DecisionOption,
    DecisionOutcome,
    DecisionRisk,
)


def test_decision_required_fields(sample_decision: Decision) -> None:
    assert sample_decision.decision_id == "dec_proxy_preview_fixture"
    assert sample_decision.domain == DecisionDomain.ENDPOINT_RELIABILITY
    assert sample_decision.title
    assert len(sample_decision.evidence) >= 1
    assert 0.0 <= sample_decision.confidence <= 1.0
    assert 0.0 <= sample_decision.risk_score <= 100.0
    assert sample_decision.expected_outcome.label
    assert len(sample_decision.alternative_options) >= 1


def test_decision_missing_evidence_rejected() -> None:
    with pytest.raises(ValidationError):
        Decision(
            decision_id="dec_bad",
            domain="generic",
            title="Incomplete",
            evidence=[],
            confidence=0.5,
            risk_score=10.0,
            expected_outcome=DecisionOutcome(label="noop"),
            alternative_options=[
                DecisionOption(label="wait", confidence=0.5, risk_score=5.0),
            ],
        )


def test_confidence_bounds() -> None:
    base = {
        "decision_id": "dec_bounds",
        "domain": "generic",
        "title": "Bounds test",
        "evidence": [DecisionEvidence(label="obs", kind="observation")],
        "risk_score": 10.0,
        "expected_outcome": DecisionOutcome(label="ok"),
        "alternative_options": [DecisionOption(label="a", confidence=0.5, risk_score=1.0)],
    }
    with pytest.raises(ValidationError):
        Decision(**base, confidence=1.5)
    with pytest.raises(ValidationError):
        Decision(**base, confidence=-0.1)


def test_nested_models_round_trip(sample_decision: Decision) -> None:
    dumped = sample_decision.model_dump(mode="json")
    restored = Decision.model_validate(dumped)
    assert restored.decision_id == sample_decision.decision_id
    assert restored.evidence[0].kind == sample_decision.evidence[0].kind
    assert restored.context is not None
    assert restored.context.run_id == "run_fixture_001"
    assert restored.explanation is not None
    assert restored.explanation.policy_status == "PREVIEW"


def test_decision_option_and_risk_fields() -> None:
    opt = DecisionOption(
        label="Preview only",
        description="No execute",
        confidence=0.7,
        risk_score=20.0,
        recommended=True,
        policy_gate="PREVIEW",
    )
    risk = DecisionRisk(
        category="data_loss",
        score=80.0,
        severity="high",
        mitigations=["backup"],
    )
    assert opt.recommended is True
    assert risk.severity == "high"
    assert risk.mitigations == ["backup"]


def test_decision_context_metadata() -> None:
    ctx = DecisionContext(
        domain="market_events",
        subject_id="research-desk",
        metadata={"event_id": "CPI_2026_06"},
    )
    assert ctx.domain == "market_events"
    assert ctx.metadata["event_id"] == "CPI_2026_06"


def test_decision_explanation_drivers() -> None:
    expl = DecisionExplanation(
        summary="Test summary",
        main_drivers=["driver_a"],
        limitations=["observation is not proof"],
    )
    assert expl.main_drivers == ["driver_a"]

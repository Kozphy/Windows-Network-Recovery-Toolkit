"""Unified platform outcome metrics."""

from __future__ import annotations

from src.platform.models import DecisionOption
from src.platform.outcome_engine import compute_metrics, record_outcome


def test_outcome_metrics_unified() -> None:
    dec = DecisionOption(
        decision_id="dec-1",
        event_id="e1",
        title="Research",
        action_type="research",
        confidence=0.7,
        risk_score=0.1,
    )
    oc = record_outcome(dec, success=True, observed_result="ok")
    m = compute_metrics([oc], {"dec-1": dec}, domain_by_decision={"dec-1": "windows"})
    assert m.decision_accuracy == 1.0
    assert m.success_rate == 1.0
    assert m.average_confidence == 0.7

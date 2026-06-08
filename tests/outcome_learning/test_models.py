from __future__ import annotations

import pytest
from pydantic import ValidationError

from platform_core.outcome_learning import DecisionOutcome


def test_decision_outcome_required_fields() -> None:
    record = DecisionOutcome(
        decision_id="dec_test",
        outcome="resolved",
        success=True,
        cost=10.0,
        time_to_resolution=30.0,
        notes="ok",
    )
    assert record.decision_id == "dec_test"
    assert record.cost == 10.0


def test_negative_cost_rejected() -> None:
    with pytest.raises(ValidationError):
        DecisionOutcome(
            decision_id="dec_test",
            outcome="x",
            success=True,
            cost=-1.0,
        )

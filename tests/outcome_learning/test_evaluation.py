from __future__ import annotations

from platform_core.outcome_learning import (
    DecisionOutcome,
    classify_outcome,
    evaluate_outcome,
    evaluate_outcomes,
)


def test_classify_true_positive() -> None:
    assert classify_outcome(predicted_success=True, actual_success=True) == "true_positive"


def test_classify_false_positive() -> None:
    assert classify_outcome(predicted_success=True, actual_success=False) == "false_positive"


def test_evaluate_outcome_correctness() -> None:
    record = DecisionOutcome(
        decision_id="dec_a",
        outcome="worked",
        success=True,
        predicted_success=True,
    )
    evaluation = evaluate_outcome(record)
    assert evaluation.correct is True
    assert evaluation.classification == "true_positive"


def test_evaluate_outcomes_sorted(sample_outcomes) -> None:
    evaluations = evaluate_outcomes(sample_outcomes)
    ids = [row.decision_id for row in evaluations]
    assert ids == sorted(ids)

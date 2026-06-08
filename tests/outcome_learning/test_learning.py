from __future__ import annotations

from platform_core.outcome_learning import (
    DecisionOutcome,
    compute_learning_metrics,
    evaluate_outcomes,
)


def test_metrics_on_fixture_batch(sample_outcomes) -> None:
    evaluations = evaluate_outcomes(sample_outcomes)
    metrics = compute_learning_metrics(evaluations)
    assert metrics.sample_count == 5
    assert 0.0 <= metrics.decision_accuracy <= 1.0
    assert 0.0 <= metrics.decision_precision <= 1.0
    assert 0.0 <= metrics.decision_recall <= 1.0
    assert metrics.average_cost >= 0.0


def test_metrics_manual_confusion_matrix() -> None:
    records = [
        DecisionOutcome(decision_id="d1", outcome="a", success=True, predicted_success=True, cost=10),
        DecisionOutcome(decision_id="d2", outcome="b", success=False, predicted_success=True, cost=20),
        DecisionOutcome(decision_id="d3", outcome="c", success=True, predicted_success=False, cost=5),
        DecisionOutcome(decision_id="d4", outcome="d", success=False, predicted_success=False, cost=0),
    ]
    metrics = compute_learning_metrics(evaluate_outcomes(records))
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_negatives == 1
    assert metrics.decision_accuracy == 0.5
    assert metrics.decision_precision == 0.5
    assert metrics.decision_recall == 0.5
    assert metrics.average_cost == 8.75


def test_empty_batch_returns_zero_metrics() -> None:
    metrics = compute_learning_metrics([])
    assert metrics.sample_count == 0
    assert metrics.decision_accuracy == 0.0

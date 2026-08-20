from research.experiments.evaluate_binary import evaluate


def test_binary_metrics_are_computed_from_confusion_counts() -> None:
    rows = [
        {
            "scenario_id": "a",
            "ground_truth_drift": True,
            "predictions": {"context": True},
        },
        {
            "scenario_id": "b",
            "ground_truth_drift": False,
            "predictions": {"context": True},
        },
        {
            "scenario_id": "c",
            "ground_truth_drift": False,
            "predictions": {"context": False},
        },
        {
            "scenario_id": "d",
            "ground_truth_drift": True,
            "predictions": {"context": False},
        },
    ]

    result = evaluate(rows, "context")

    assert result.n == 4
    assert (result.tp, result.fp, result.tn, result.fn) == (1, 1, 1, 1)
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.f1 == 0.5
    assert result.fpr == 0.5
    assert result.fnr == 0.5


def test_undefined_denominator_is_not_silently_zero() -> None:
    rows = [
        {
            "scenario_id": "negative-only",
            "ground_truth_drift": False,
            "predictions": {"context": False},
        }
    ]

    result = evaluate(rows, "context")

    assert result.precision is None
    assert result.recall is None
    assert result.f1 is None
    assert result.fnr is None
    assert result.fpr == 0.0

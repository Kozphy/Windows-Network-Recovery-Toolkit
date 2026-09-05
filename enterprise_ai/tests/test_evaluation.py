from enterprise_ai.evaluation import evaluate_binary_predictions


def test_evaluation_returns_metrics():
    result = evaluate_binary_predictions([0, 1, 1, 0], [0.1, 0.9, 0.8, 0.2])
    assert result.accuracy == 1.0
    assert result.recall == 1.0
    assert result.passed is True


def test_bad_model_fails_gate():
    result = evaluate_binary_predictions([0, 1, 1, 0], [0.9, 0.1, 0.2, 0.8])
    assert result.passed is False

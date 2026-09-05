from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationResult:
    accuracy: float
    precision: float
    recall: float
    brier_score: float
    passed: bool


def evaluate_binary_predictions(
    y_true: list[int], probabilities: list[float], threshold: float = 0.5
) -> EvaluationResult:
    if len(y_true) != len(probabilities) or not y_true:
        raise ValueError("y_true and probabilities must be non-empty and have equal length")
    preds = [1 if p >= threshold else 0 for p in probabilities]
    tp = sum(1 for y, p in zip(y_true, preds) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, preds) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, preds) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, preds) if y == 1 and p == 0)
    accuracy = (tp + tn) / len(y_true)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    brier = sum((p - y) ** 2 for y, p in zip(y_true, probabilities)) / len(y_true)
    passed = accuracy >= 0.80 and recall >= 0.70 and brier <= 0.20
    return EvaluationResult(accuracy, precision, recall, brier, passed)

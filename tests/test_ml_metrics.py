import numpy as np
import pandas as pd

from ml.train_models import evaluate


def test_evaluate_returns_core_metrics():
    y = pd.Series([0, 0, 1, 1])
    prob = np.array([0.1, 0.3, 0.7, 0.9])
    metrics = evaluate(y, prob)

    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert 0.0 <= metrics["brier"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0

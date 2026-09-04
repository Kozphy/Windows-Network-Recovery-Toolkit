from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "run_benchmark.py"
spec = importlib.util.spec_from_file_location("research_benchmark", MODULE_PATH)
benchmark = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(benchmark)


def _frame(rows: int = 40) -> pd.DataFrame:
    return pd.DataFrame({
        "observed_at": pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC"),
        "proxy_drift": [i % 2 for i in range(rows)],
        "tls_failures": [i % 3 for i in range(rows)],
        "dns_latency": np.linspace(10, 100, rows),
        "failure_label": [i % 2 for i in range(rows)],
    })


def test_temporal_split_preserves_past_to_future_order():
    frame = _frame().sample(frac=1.0, random_state=7)
    x_train, x_test, y_train, y_test, summary = benchmark._temporal_split(frame, "observed_at", 0.2)
    assert len(x_train) == len(y_train) == summary.train_rows
    assert len(x_test) == len(y_test) == summary.test_rows
    assert summary.strategy == "temporal"
    ordered = frame.sort_values("observed_at")
    boundary = summary.train_rows
    assert ordered.iloc[boundary - 1]["observed_at"] < ordered.iloc[boundary]["observed_at"]


def test_ablation_sets_remove_named_feature_groups():
    sets = benchmark._ablation_sets(["proxy_drift", "tls_failures", "dns_latency", "other"])
    assert "proxy_drift" not in sets["without_proxy"]
    assert "tls_failures" not in sets["without_tls"]
    assert "dns_latency" not in sets["without_dns"]
    assert len(sets["full"]) == 4


def test_evaluate_returns_primary_probability_metrics():
    y = pd.Series([0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    result = benchmark._evaluate(y, p)
    for name in ("precision", "recall", "f1", "brier", "roc_auc", "pr_auc"):
        assert name in result
    assert result["f1"] == pytest.approx(1.0)


def test_bootstrap_ci_is_ordered_and_deterministic():
    y = pd.Series([0, 0, 1, 1] * 10)
    p = np.array([0.1, 0.2, 0.8, 0.9] * 10)
    first = benchmark._bootstrap_f1_ci(y, p, 100)
    second = benchmark._bootstrap_f1_ci(y, p, 100)
    assert first == second
    assert first["lower"] <= first["median"] <= first["upper"]

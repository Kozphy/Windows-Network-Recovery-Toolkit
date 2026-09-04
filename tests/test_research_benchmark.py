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
    for name in ("precision", "recall", "f1", "false_positive_rate", "brier", "roc_auc", "pr_auc"):
        assert name in result
    assert result["f1"] == pytest.approx(1.0)
    assert result["false_positive_rate"] == pytest.approx(0.0)


def test_bootstrap_ci_is_ordered_and_deterministic():
    y = pd.Series([0, 0, 1, 1] * 10)
    p = np.array([0.1, 0.2, 0.8, 0.9] * 10)
    first = benchmark._bootstrap_f1_ci(y, p, 100)
    second = benchmark._bootstrap_f1_ci(y, p, 100)
    assert first == second
    assert first["lower"] <= first["median"] <= first["upper"]


def test_rules_probability_uses_same_holdout_features():
    frame = pd.DataFrame({
        "proxy_drift": [0, 1, 1],
        "tls_failures": [0, 0, 2],
        "dns_failure_rate": [0.0, 0.0, 0.2],
        "other": [99, 99, 99],
    })
    probability = benchmark._rules_probability(frame)
    assert probability[0] == pytest.approx(0.0)
    assert probability[1] == pytest.approx(1 / 3)
    assert probability[2] == pytest.approx(1.0)


def test_calibration_diagnostics_reports_ece_and_reliability_bins():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.05, 0.15, 0.85, 0.95])
    result = benchmark._calibration_diagnostics(y, p, bins=4)
    assert 0.0 <= result["ece"] <= 1.0
    assert result["reliability"]
    assert sum(row["count"] for row in result["reliability"]) == len(y)


def test_paired_bootstrap_delta_is_deterministic_and_detects_better_candidate():
    y = np.array([0, 0, 1, 1] * 20)
    candidate = np.array([0.1, 0.2, 0.8, 0.9] * 20)
    baseline = np.array([0.9, 0.8, 0.2, 0.1] * 20)
    first = benchmark._paired_bootstrap_f1_delta(y, candidate, baseline, 100)
    second = benchmark._paired_bootstrap_f1_delta(y, candidate, baseline, 100)
    assert first == second
    assert first["median"] > 0
    assert first["probability_candidate_better"] > 0.95

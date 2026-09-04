from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_STATE = 42
TARGET = "failure_label"


@dataclass(frozen=True)
class SplitSummary:
    strategy: str
    train_rows: int
    test_rows: int
    train_positive_rate: float
    test_positive_rate: float
    timestamp_column: str | None = None


def _preprocessor(frame: pd.DataFrame) -> ColumnTransformer:
    numeric = frame.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    categorical = [column for column in frame.columns if column not in numeric]
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ]
    )


def _models(frame: pd.DataFrame) -> dict[str, Pipeline]:
    pre = _preprocessor(frame)
    return {
        "logistic_regression": Pipeline(
            [
                ("preprocess", clone(pre)),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", clone(pre)),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def _temporal_split(
    data: pd.DataFrame,
    timestamp_column: str,
    test_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, SplitSummary]:
    if timestamp_column not in data.columns:
        raise ValueError(f"Timestamp column not found: {timestamp_column}")
    ordered = data.copy()
    ordered[timestamp_column] = pd.to_datetime(ordered[timestamp_column], utc=True, errors="raise")
    ordered = ordered.sort_values(timestamp_column, kind="mergesort").reset_index(drop=True)
    split_at = max(1, min(len(ordered) - 1, int(round(len(ordered) * (1 - test_fraction)))))
    train = ordered.iloc[:split_at]
    test = ordered.iloc[split_at:]
    feature_columns = [column for column in ordered.columns if column not in {TARGET, timestamp_column}]
    x_train, x_test = train[feature_columns], test[feature_columns]
    y_train, y_test = train[TARGET].astype(int), test[TARGET].astype(int)
    summary = SplitSummary(
        strategy="temporal",
        train_rows=len(train),
        test_rows=len(test),
        train_positive_rate=float(y_train.mean()),
        test_positive_rate=float(y_test.mean()),
        timestamp_column=timestamp_column,
    )
    return x_train, x_test, y_train, y_test, summary


def _evaluate(y_true: pd.Series, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(int)
    metrics: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "brier": float(brier_score_loss(y_true, probability)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probability))
        metrics["pr_auc"] = float(average_precision_score(y_true, probability))
    return metrics


def _bootstrap_f1_ci(
    y_true: pd.Series,
    probability: np.ndarray,
    iterations: int,
    alpha: float = 0.05,
) -> dict[str, float | int]:
    rng = np.random.default_rng(RANDOM_STATE)
    y = np.asarray(y_true)
    scores: list[float] = []
    for _ in range(iterations):
        sample = rng.integers(0, len(y), size=len(y))
        pred = (probability[sample] >= 0.5).astype(int)
        scores.append(float(f1_score(y[sample], pred, zero_division=0)))
    return {
        "iterations": iterations,
        "lower": float(np.quantile(scores, alpha / 2)),
        "median": float(np.quantile(scores, 0.5)),
        "upper": float(np.quantile(scores, 1 - alpha / 2)),
    }


def _fit_probability_model(model: Pipeline, x_train: pd.DataFrame, y_train: pd.Series, calibrate: bool) -> Any:
    if not calibrate:
        return model.fit(x_train, y_train)
    calibrated = CalibratedClassifierCV(model, method="sigmoid", cv=3)
    return calibrated.fit(x_train, y_train)


def _ablation_sets(columns: list[str]) -> dict[str, list[str]]:
    sets = {"full": columns}
    groups = {
        "without_proxy": [column for column in columns if "proxy" not in column.lower()],
        "without_tls": [column for column in columns if "tls" not in column.lower()],
        "without_dns": [column for column in columns if "dns" not in column.lower()],
    }
    for name, subset in groups.items():
        if subset and subset != columns:
            sets[name] = subset
    return sets


def run(args: argparse.Namespace) -> dict[str, Any]:
    data = pd.read_csv(args.data)
    if TARGET not in data.columns:
        raise ValueError(f"Dataset must contain target column: {TARGET}")
    if len(data) < 20:
        raise ValueError("Research benchmark requires at least 20 rows.")
    labels = set(data[TARGET].dropna().astype(int).unique().tolist())
    if not labels.issubset({0, 1}) or len(labels) < 2:
        raise ValueError("failure_label must be binary and contain both classes.")

    x_train, x_test, y_train, y_test, split = _temporal_split(
        data,
        args.timestamp_column,
        args.test_fraction,
    )
    if y_train.nunique() < 2:
        raise ValueError("Training window must contain both classes for supervised benchmarking.")

    results: dict[str, Any] = {}
    for ablation_name, columns in _ablation_sets(x_train.columns.tolist()).items():
        train_view = x_train[columns]
        test_view = x_test[columns]
        for model_name, model in _models(train_view).items():
            fitted = _fit_probability_model(model, train_view, y_train, args.calibrate)
            probability = fitted.predict_proba(test_view)[:, 1]
            key = f"{model_name}:{ablation_name}"
            results[key] = {
                "model": model_name,
                "ablation": ablation_name,
                "features": columns,
                "calibrated": bool(args.calibrate),
                "metrics": _evaluate(y_test, probability),
                "f1_bootstrap_ci": _bootstrap_f1_ci(y_test, probability, args.bootstrap_iterations),
            }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "research_contract": "Level 7 benchmark; demo/synthetic data must not be presented as production evidence.",
        "target": TARGET,
        "split": asdict(split),
        "results": results,
    }
    (out / "benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    rows = []
    for key, item in results.items():
        rows.append({"run": key, **item["metrics"], "ci_lower": item["f1_bootstrap_ci"]["lower"], "ci_upper": item["f1_bootstrap_ci"]["upper"]})
    pd.DataFrame(rows).to_csv(out / "benchmark.csv", index=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible temporal technology-risk benchmarks.")
    parser.add_argument("--data", required=True, help="CSV containing failure_label and a timestamp column.")
    parser.add_argument("--timestamp-column", default="observed_at")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--out", default="research/results/latest")
    args = parser.parse_args()
    if not 0.05 <= args.test_fraction <= 0.5:
        raise ValueError("--test-fraction must be between 0.05 and 0.5")
    if args.bootstrap_iterations < 100:
        raise ValueError("--bootstrap-iterations must be at least 100")
    report = run(args)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

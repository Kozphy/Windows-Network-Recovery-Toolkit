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
    confusion_matrix,
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


def _evaluate(y_true: pd.Series | np.ndarray, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    negative_count = tn + fp
    metrics: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "false_positive_rate": float(fp / negative_count) if negative_count else 0.0,
        "brier": float(brier_score_loss(y_true, probability)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probability))
        metrics["pr_auc"] = float(average_precision_score(y_true, probability))
    return metrics


def _calibration_diagnostics(
    y_true: pd.Series | np.ndarray,
    probability: np.ndarray,
    bins: int = 10,
) -> dict[str, Any]:
    """Return ECE and reliability-bin evidence without plotting dependencies."""
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probability, dtype=float)
    if len(y) != len(p) or len(y) == 0:
        raise ValueError("Calibration diagnostics require non-empty aligned arrays")
    p = np.clip(p, 0.0, 1.0)
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, float | int]] = []
    ece = 0.0
    for index in range(bins):
        left, right = edges[index], edges[index + 1]
        mask = (p >= left) & ((p < right) if index < bins - 1 else (p <= right))
        count = int(mask.sum())
        if count == 0:
            continue
        mean_confidence = float(p[mask].mean())
        observed_rate = float(y[mask].mean())
        gap = abs(mean_confidence - observed_rate)
        ece += (count / len(y)) * gap
        rows.append(
            {
                "bin": index,
                "count": count,
                "mean_probability": mean_confidence,
                "observed_positive_rate": observed_rate,
                "absolute_gap": float(gap),
            }
        )
    return {"bins": bins, "ece": float(ece), "reliability": rows}


def _rules_probability(frame: pd.DataFrame) -> np.ndarray:
    """Deterministic rules-only comparator on the same holdout rows.

    This intentionally stays simple. It is a comparator, not a tuned replacement for
    the toolkit's full control engine. Numeric proxy/WinHTTP/TLS/DNS signals contribute
    one rule vote when non-zero. The score is the fraction of triggered available rules.
    """
    rule_columns = [
        column
        for column in frame.columns
        if any(token in column.lower() for token in ("proxy", "winhttp", "tls", "dns"))
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not rule_columns:
        return np.zeros(len(frame), dtype=float)
    votes = np.column_stack(
        [pd.to_numeric(frame[column], errors="coerce").fillna(0).to_numpy() > 0 for column in rule_columns]
    )
    return votes.mean(axis=1).astype(float)


def _bootstrap_f1_ci(
    y_true: pd.Series | np.ndarray,
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


def _paired_bootstrap_f1_delta(
    y_true: pd.Series | np.ndarray,
    candidate_probability: np.ndarray,
    baseline_probability: np.ndarray,
    iterations: int,
    alpha: float = 0.05,
) -> dict[str, float | int]:
    """Paired bootstrap CI for candidate F1 minus rules-only baseline F1."""
    y = np.asarray(y_true)
    candidate_probability = np.asarray(candidate_probability)
    baseline_probability = np.asarray(baseline_probability)
    if not (len(y) == len(candidate_probability) == len(baseline_probability)):
        raise ValueError("Paired comparison arrays must have equal length")
    rng = np.random.default_rng(RANDOM_STATE)
    deltas: list[float] = []
    for _ in range(iterations):
        sample = rng.integers(0, len(y), size=len(y))
        candidate = (candidate_probability[sample] >= 0.5).astype(int)
        baseline = (baseline_probability[sample] >= 0.5).astype(int)
        deltas.append(
            float(
                f1_score(y[sample], candidate, zero_division=0)
                - f1_score(y[sample], baseline, zero_division=0)
            )
        )
    lower = float(np.quantile(deltas, alpha / 2))
    upper = float(np.quantile(deltas, 1 - alpha / 2))
    return {
        "iterations": iterations,
        "lower": lower,
        "median": float(np.quantile(deltas, 0.5)),
        "upper": upper,
        "probability_candidate_better": float(np.mean(np.asarray(deltas) > 0)),
        "interval_excludes_zero": bool(lower > 0 or upper < 0),
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

    rules_probability = _rules_probability(x_test)
    rules_result = {
        "model": "rules_only",
        "ablation": "full",
        "features": [
            column
            for column in x_test.columns
            if any(token in column.lower() for token in ("proxy", "winhttp", "tls", "dns"))
            and pd.api.types.is_numeric_dtype(x_test[column])
        ],
        "calibrated": False,
        "metrics": _evaluate(y_test, rules_probability),
        "calibration": _calibration_diagnostics(y_test, rules_probability, args.calibration_bins),
        "f1_bootstrap_ci": _bootstrap_f1_ci(y_test, rules_probability, args.bootstrap_iterations),
    }

    results: dict[str, Any] = {"rules_only:full": rules_result}
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
                "calibration": _calibration_diagnostics(y_test, probability, args.calibration_bins),
                "f1_bootstrap_ci": _bootstrap_f1_ci(y_test, probability, args.bootstrap_iterations),
                "paired_vs_rules_f1_delta": _paired_bootstrap_f1_delta(
                    y_test,
                    probability,
                    rules_probability,
                    args.bootstrap_iterations,
                ),
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
        paired = item.get("paired_vs_rules_f1_delta", {})
        rows.append(
            {
                "run": key,
                **item["metrics"],
                "ece": item["calibration"]["ece"],
                "ci_lower": item["f1_bootstrap_ci"]["lower"],
                "ci_upper": item["f1_bootstrap_ci"]["upper"],
                "f1_delta_vs_rules": paired.get("median"),
                "f1_delta_ci_lower": paired.get("lower"),
                "f1_delta_ci_upper": paired.get("upper"),
            }
        )
    pd.DataFrame(rows).to_csv(out / "benchmark.csv", index=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible temporal technology-risk benchmarks.")
    parser.add_argument("--data", required=True, help="CSV containing failure_label and a timestamp column.")
    parser.add_argument("--timestamp-column", default="observed_at")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--calibration-bins", type=int, default=10)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--out", default="research/results/latest")
    args = parser.parse_args()
    if not 0.05 <= args.test_fraction <= 0.5:
        raise ValueError("--test-fraction must be between 0.05 and 0.5")
    if args.bootstrap_iterations < 100:
        raise ValueError("--bootstrap-iterations must be at least 100")
    if args.calibration_bins < 2:
        raise ValueError("--calibration-bins must be at least 2")
    report = run(args)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

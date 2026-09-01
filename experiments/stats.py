"""Bootstrap confidence intervals for benchmark metrics."""

from __future__ import annotations

import csv
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from experiments.metrics import _normalize_label


@dataclass
class BootstrapResult:
    metric: str
    baseline: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    sample_size: int
    n_bootstrap: int
    random_seed: int
    method: str = "percentile_bootstrap"
    assumptions: str = "IID resampling of cases; bounded accuracy/F1 metrics."
    interpretation: str = "95% CI for metric under case resampling."
    limitations: str = "Small fixture benchmark; not enterprise-scale inference."


def _macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    f1s: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)
        if tp + fn == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        f1s.append(f1)
    return sum(f1s) / len(f1s) if f1s else 0.0


def bootstrap_metric(
    y_true: list[str],
    y_pred: list[str],
    metric_fn: Callable[[list[str], list[str]], float],
    *,
    n_bootstrap: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    n = len(y_true)
    if n == 0:
        return 0.0, 0.0, 0.0
    point = metric_fn(y_true, y_pred)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_bootstrap):
        indices = [rng.randrange(n) for _ in range(n)]
        yt = [y_true[i] for i in indices]
        yp = [y_pred[i] for i in indices]
        samples.append(metric_fn(yt, yp))
    samples.sort()
    lower_idx = int((alpha / 2) * n_bootstrap)
    upper_idx = int((1 - alpha / 2) * n_bootstrap) - 1
    return point, samples[lower_idx], samples[upper_idx]


def build_statistical_summary(
    baseline: str,
    y_true: list[str],
    y_pred: list[str],
    *,
    seed: int = 42,
) -> list[BootstrapResult]:
    y_true = [_normalize_label(x) for x in y_true]
    y_pred = [_normalize_label(x) for x in y_pred]
    n = len(y_true)
    results: list[BootstrapResult] = []
    for metric_name, fn in (
        ("accuracy", lambda yt, yp: sum(t == p for t, p in zip(yt, yp, strict=True)) / len(yt)),
        ("macro_f1", _macro_f1),
        (
            "abstention_rate",
            lambda yt, yp: sum(
                1 for p in yp if p in {"ERROR_INSUFFICIENT_DATA", "INSUFFICIENT_DATA", "UNKNOWN"}
            )
            / len(yp),
        ),
    ):
        point, lo, hi = bootstrap_metric(y_true, y_pred, fn, seed=seed)
        results.append(
            BootstrapResult(
                metric=metric_name,
                baseline=baseline,
                point_estimate=point,
                ci_lower=lo,
                ci_upper=hi,
                sample_size=n,
                n_bootstrap=1000,
                random_seed=seed,
            )
        )
    return results


def write_statistical_summary_csv(path: Path, rows: list[BootstrapResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "metric",
        "baseline",
        "point_estimate",
        "ci_lower",
        "ci_upper",
        "sample_size",
        "n_bootstrap",
        "random_seed",
        "method",
        "assumptions",
        "interpretation",
        "limitations",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "metric": row.metric,
                    "baseline": row.baseline,
                    "point_estimate": f"{row.point_estimate:.4f}",
                    "ci_lower": f"{row.ci_lower:.4f}",
                    "ci_upper": f"{row.ci_upper:.4f}",
                    "sample_size": row.sample_size,
                    "n_bootstrap": row.n_bootstrap,
                    "random_seed": row.random_seed,
                    "method": row.method,
                    "assumptions": row.assumptions,
                    "interpretation": row.interpretation,
                    "limitations": row.limitations,
                }
            )

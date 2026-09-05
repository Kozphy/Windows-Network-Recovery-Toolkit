"""Statistical analysis for 2x2 factorial interaction effects."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Literal

from research.interactions.models import (
    CellSummary,
    InteractionAnalysisResult,
    InteractionEffectEstimate,
    InteractionObservation,
)

OutcomeName = Literal["y_failure", "y_severity", "y_platform_failure", "y_platform_severity"]

_DEFAULT_ASSUMPTIONS = [
    "2x2 factorial with synthetic fixtures; not a field experiment.",
    "Interaction contrast = Y11 - Y10 - Y01 + Y00 on cell means.",
    "Linear probability / severity scale — not logistic regression.",
    "Small sample sizes — CIs are exploratory, not confirmatory.",
]

_DEFAULT_LIMITATIONS = [
    "Do not claim statistical significance without adequate sample size and assumptions.",
    "Designed ground-truth severity may not match platform classifier response.",
    "Correlation in replicates within a cell is not modeled.",
]


def _outcome_value(obs: InteractionObservation, outcome: OutcomeName) -> float:
    return float(getattr(obs, outcome))


def _cell_summaries(
    observations: list[InteractionObservation],
    outcome: OutcomeName,
) -> list[CellSummary]:
    buckets: dict[tuple[int, int], list[InteractionObservation]] = defaultdict(list)
    for obs in observations:
        buckets[(obs.x1, obs.x2)].append(obs)

    summaries: list[CellSummary] = []
    for (x1, x2), rows in sorted(buckets.items()):
        n = len(rows)
        summaries.append(
            CellSummary(
                x1=x1,
                x2=x2,
                n=n,
                mean_y_failure=sum(r.y_failure for r in rows) / n,
                mean_y_severity=sum(r.y_severity for r in rows) / n,
                mean_platform_failure=sum(r.y_platform_failure for r in rows) / n,
                mean_platform_severity=sum(r.y_platform_severity for r in rows) / n,
            )
        )
    return summaries


def _cell_mean(summaries: list[CellSummary], x1: int, x2: int, outcome: OutcomeName) -> float:
    for cell in summaries:
        if cell.x1 == x1 and cell.x2 == x2:
            if outcome == "y_failure":
                return cell.mean_y_failure
            if outcome == "y_severity":
                return cell.mean_y_severity
            if outcome == "y_platform_failure":
                return cell.mean_platform_failure
            return cell.mean_platform_severity
    return 0.0


def interaction_contrast(
    y00: float,
    y10: float,
    y01: float,
    y11: float,
) -> tuple[float, float, float]:
    """Return main effect x1, main effect x2, interaction (additive contrast)."""
    main_x1 = ((y10 + y11) / 2.0) - ((y00 + y01) / 2.0)
    main_x2 = ((y01 + y11) / 2.0) - ((y00 + y10) / 2.0)
    interaction = y11 - y10 - y01 + y00
    return main_x1, main_x2, interaction


def fit_lpm_coefficients(
    observations: list[InteractionObservation],
    outcome: OutcomeName,
) -> tuple[float, float, float, float]:
    """OLS for Y ~ 1 + X1 + X2 + X1*X2 (linear probability / severity model)."""
    xs: list[list[float]] = []
    ys: list[float] = []
    for obs in observations:
        xs.append([1.0, float(obs.x1), float(obs.x2), float(obs.x1 * obs.x2)])
        ys.append(_outcome_value(obs, outcome))

    return _ols_solve(xs, ys)


def _ols_solve(x: list[list[float]], y: list[float]) -> tuple[float, float, float, float]:
    p = len(x[0])
    n = len(x)
    if n < p:
        return (0.0, 0.0, 0.0, 0.0)

    # XtX and Xty
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for i in range(n):
        for r in range(p):
            xty[r] += x[i][r] * y[i]
            for c in range(p):
                xtx[r][c] += x[i][r] * x[i][c]

    beta = _gaussian_solve(xtx, xty)
    return (beta[0], beta[1], beta[2], beta[3])


def _gaussian_solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    aug = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[pivot][col]):
                pivot = row
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_val = aug[col][col]
        if abs(pivot_val) < 1e-12:
            continue
        for row in range(col + 1, n):
            factor = aug[row][col] / pivot_val
            for c in range(col, n + 1):
                aug[row][c] -= factor * aug[col][c]
    result = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(aug[i][i]) < 1e-12:
            result[i] = 0.0
            continue
        result[i] = (aug[i][n] - sum(aug[i][j] * result[j] for j in range(i + 1, n))) / aug[i][i]
    return result


def bootstrap_interaction_ci(
    observations: list[InteractionObservation],
    outcome: OutcomeName,
    *,
    seed: int = 42,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Bootstrap CI for interaction contrast on cell means."""
    if len(observations) < 4:
        return (0.0, 0.0)

    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_bootstrap):
        draw = [observations[rng.randrange(len(observations))] for _ in observations]
        summaries = _cell_summaries(draw, outcome)
        _, _, interaction = interaction_contrast(
            _cell_mean(summaries, 0, 0, outcome),
            _cell_mean(summaries, 1, 0, outcome),
            _cell_mean(summaries, 0, 1, outcome),
            _cell_mean(summaries, 1, 1, outcome),
        )
        samples.append(interaction)
    samples.sort()
    lo = int((alpha / 2) * n_bootstrap)
    hi = int((1 - alpha / 2) * n_bootstrap) - 1
    return samples[lo], samples[hi]


def analyze_outcome(
    observations: list[InteractionObservation],
    outcome: OutcomeName,
    *,
    seed: int = 42,
    bootstrap: bool = True,
) -> InteractionEffectEstimate:
    summaries = _cell_summaries(observations, outcome)
    y00 = _cell_mean(summaries, 0, 0, outcome)
    y10 = _cell_mean(summaries, 1, 0, outcome)
    y01 = _cell_mean(summaries, 0, 1, outcome)
    y11 = _cell_mean(summaries, 1, 1, outcome)
    main_x1, main_x2, interaction = interaction_contrast(y00, y10, y01, y11)

    beta_0, beta_1, beta_2, beta_3 = fit_lpm_coefficients(observations, outcome)

    ci_lo: float | None = None
    ci_hi: float | None = None
    ci_method: str | None = None
    if bootstrap and len(observations) >= 8:
        ci_lo, ci_hi = bootstrap_interaction_ci(observations, outcome, seed=seed)
        ci_method = "percentile_bootstrap_cell_contrast"

    limitations = list(_DEFAULT_LIMITATIONS)
    if len(observations) < 12:
        limitations.append(f"Small n={len(observations)}; interpret CIs cautiously.")

    return InteractionEffectEstimate(
        outcome=outcome,
        main_effect_x1=main_x1,
        main_effect_x2=main_x2,
        interaction_effect=interaction,
        lpm_beta_0=beta_0,
        lpm_beta_1=beta_1,
        lpm_beta_2=beta_2,
        lpm_beta_3=beta_3,
        sample_size=len(observations),
        cell_summaries=summaries,
        ci_lower=ci_lo,
        ci_upper=ci_hi,
        ci_method=ci_method,
        effect_size_label="additive_contrast",
        limitations=limitations,
    )


def analyze_experiment(
    experiment_id: str,
    observations: list[InteractionObservation],
    *,
    factor_a_name: str,
    factor_b_name: str,
    description: str,
    git_sha: str = "unknown",
    dataset_digest: str = "",
    seed: int = 42,
) -> InteractionAnalysisResult:
    rows = [o for o in observations if o.experiment_id == experiment_id]
    effects = [
        analyze_outcome(rows, "y_severity", seed=seed),
        analyze_outcome(rows, "y_failure", seed=seed),
        analyze_outcome(rows, "y_platform_severity", seed=seed),
        analyze_outcome(rows, "y_platform_failure", seed=seed),
    ]
    return InteractionAnalysisResult(
        experiment_id=experiment_id,
        factor_a_name=factor_a_name,
        factor_b_name=factor_b_name,
        description=description,
        git_sha=git_sha,
        dataset_digest=dataset_digest,
        random_seed=seed,
        sample_size=len(rows),
        effects=effects,
        assumptions=list(_DEFAULT_ASSUMPTIONS),
        limitations=[
            "Designed factorial — ground-truth interaction may differ from platform response.",
            "No causal identification claim; observational association on fixtures only.",
        ],
    )

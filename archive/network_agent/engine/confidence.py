from __future__ import annotations

"""Confidence utilities for deterministic diagnostic scoring.

This module sits in the decision stage of the hybrid diagnostic pipeline
(collection -> decision -> report/API serving). It provides numeric helpers used
by rule-based classifiers to keep confidence values bounded and comparable.

Key invariants:
- Confidence scores are always clamped to [0.0, 1.0].
- Helpers are pure functions with no side effects.
- Given identical inputs, outputs are deterministic and idempotent.
"""


def clamp(value: float) -> float:
    """Clamp a confidence value to the closed range [0.0, 1.0].

    This guard prevents invalid confidence values from propagating to reports,
    UI rendering, or downstream policy decisions.

    Args:
        value: Raw floating-point confidence candidate.

    Returns:
        float: A normalized confidence in [0.0, 1.0].

    Raises:
        None.

    Example:
        >>> clamp(1.7)
        1.0
    """
    return max(0.0, min(1.0, value))


def score(base: float, boosts: list[float], penalties: list[float]) -> float:
    """Compute a bounded confidence score from additive rule weights.

    The function combines a base prior with positive evidence (boosts) and
    negative evidence (penalties), then clamps to a valid probability-like
    range. This supports explainable, auditable rule scoring without model
    inference.

    Engineering Notes:
        - Additive scoring was chosen for transparency and easy calibration.
        - This function avoids hidden normalization that can obscure debugging.

    Audit Notes:
        - Failure mode: mis-tuned weights can saturate at 0.0 or 1.0.
        - Detection: monitor distribution of emitted confidence values.
        - Recovery: rebalance boosts/penalties while preserving clamp invariant.

    Args:
        base: Prior confidence before evidence adjustments.
        boosts: Positive evidence weights that increase confidence.
        penalties: Negative evidence weights that decrease confidence.

    Returns:
        float: Final clamped confidence value in [0.0, 1.0].

    Raises:
        None.

    Example:
        >>> score(0.1, [0.4, 0.2], [0.05])
        0.65
    """
    return clamp(base + sum(boosts) - sum(penalties))

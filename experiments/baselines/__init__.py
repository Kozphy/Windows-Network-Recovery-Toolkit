"""Registry for deterministic research baseline adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .common import Prediction
from .connectivity import predict as predict_b0
from .flat_rules import predict as predict_b1
from .full_platform import predict as predict_b3
from .single_signal import predict as predict_b2

Predictor = Callable[[dict[str, Any]], Prediction]

BASELINES: dict[str, Predictor] = {
    "B0": predict_b0,
    "B1": predict_b1,
    "B2": predict_b2,
    "B3": predict_b3,
}


def get_predictor(name: str) -> Predictor:
    """Return a configured baseline or fail with an explicit name list."""
    try:
        return BASELINES[name]
    except KeyError as exc:
        known = ", ".join(sorted(BASELINES))
        raise ValueError(f"unknown baseline {name!r}; expected one of {known}") from exc


__all__ = ["BASELINES", "Prediction", "get_predictor"]

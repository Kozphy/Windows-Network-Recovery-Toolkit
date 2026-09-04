"""Adapters mapping existing B0–B3 predictors onto DiagnosticBaseline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from experiments.baselines.b0_connectivity import predict_b0
from experiments.baselines.b1_flat_rules import predict_b1
from experiments.baselines.b2_single_signal import predict_b2
from experiments.baselines.b3_full_platform import predict_b3
from experiments.baselines.b_ml_bernoulli import BernoulliNbBaseline
from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1

PredictFn = Callable[[BenchmarkCaseV1, dict[str, Any]], BaselinePrediction]


class FunctionBaseline:
    """Wrap a pure predict(case, fixture) function as a DiagnosticBaseline."""

    def __init__(self, name: str, predict_fn: PredictFn, *, notes: str = "") -> None:
        self._name = name
        self._predict_fn = predict_fn
        self._notes = notes

    @property
    def name(self) -> str:
        return self._name

    def fit(
        self,
        cases: list[BenchmarkCaseV1],
        fixtures: list[dict[str, Any]],
        *,
        seed: int = 42,
    ) -> None:
        return None

    def predict(self, case: BenchmarkCaseV1, fixture: dict[str, Any]) -> BaselinePrediction:
        return self._predict_fn(case, fixture)

    def predict_proba(
        self, case: BenchmarkCaseV1, fixture: dict[str, Any]
    ) -> dict[str, float] | None:
        return None

    def metadata(self) -> dict[str, Any]:
        return {
            "baseline": self._name,
            "kind": "function_adapter",
            "trainable": False,
            "notes": self._notes,
        }


def baseline_a_rules() -> FunctionBaseline:
    """Brief Baseline A — flat rules (B1)."""
    return FunctionBaseline("B1", predict_b1, notes="Flat if/else rules without proof tiers")


def baseline_b_heuristic() -> FunctionBaseline:
    """Brief Baseline B — single-signal heuristic (B2)."""
    return FunctionBaseline("B2", predict_b2, notes="WinINET proxy_state single-signal heuristic")


def baseline_d_proposed() -> FunctionBaseline:
    """Brief Baseline D — proposed evidence-tiered system (B3)."""
    return FunctionBaseline(
        "B3", predict_b3, notes="Full platform: evidence tiers, policy, limitations"
    )


def baseline_connectivity_naive() -> FunctionBaseline:
    """Weak connectivity-only baseline (B0)."""
    return FunctionBaseline("B0", predict_b0, notes="Connectivity/probe signals only")


def baseline_c_ml(*, seed: int = 42) -> BernoulliNbBaseline:
    """Brief Baseline C — classical ML (B_ML Bernoulli NB)."""
    return BernoulliNbBaseline(seed=seed)


RESEARCH_ALIAS_TO_ID = {
    "A_rules": "B1",
    "B_heuristic": "B2",
    "C_ml": "B_ML",
    "D_proposed": "B3",
    "A_naive": "B0",
}

__all__ = [
    "FunctionBaseline",
    "RESEARCH_ALIAS_TO_ID",
    "baseline_a_rules",
    "baseline_b_heuristic",
    "baseline_c_ml",
    "baseline_connectivity_naive",
    "baseline_d_proposed",
]

"""Shared diagnostic baseline protocol for research evaluation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1


@runtime_checkable
class DiagnosticBaseline(Protocol):
    """Common interface for rule, heuristic, ML, and proposed baselines."""

    @property
    def name(self) -> str:
        """Stable baseline identifier (e.g. B0, B_ML, B3)."""

    def fit(
        self,
        cases: list[BenchmarkCaseV1],
        fixtures: list[dict[str, Any]],
        *,
        seed: int = 42,
    ) -> None:
        """Optional training. Rule baselines may no-op."""

    def predict(self, case: BenchmarkCaseV1, fixture: dict[str, Any]) -> BaselinePrediction:
        """Predict one case. Must not read ground-truth labels from ``case``."""

    def predict_proba(
        self, case: BenchmarkCaseV1, fixture: dict[str, Any]
    ) -> dict[str, float] | None:
        """Class probabilities when meaningful; otherwise None."""

    def metadata(self) -> dict[str, Any]:
        """Model/version notes for experiment metadata."""

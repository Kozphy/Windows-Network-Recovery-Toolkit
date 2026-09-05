"""Phase 1 — interaction effects research (factorial fault designs)."""

from research.interactions.analysis import analyze_experiment
from research.interactions.experiment import run_interaction_experiments
from research.interactions.models import InteractionAnalysisResult, InteractionCase

__all__ = [
    "InteractionAnalysisResult",
    "InteractionCase",
    "analyze_experiment",
    "run_interaction_experiments",
]

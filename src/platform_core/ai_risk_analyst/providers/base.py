"""Base analyst provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.platform_core.ai_risk_analyst.models import AIRecommendation, AnalystEvidenceBundle


class AnalystProvider(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, bundle: AnalystEvidenceBundle) -> AIRecommendation:
        """Produce advisory recommendation from structured evidence."""

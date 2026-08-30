"""Optional model-risk analytics for review prioritization.

This package never grants execution authority and is not part of the
deterministic remediation safety boundary.
"""

from .contracts import ModelRecommendation, RiskFeatures
from .scoring import deterministic_recurrence_score

__all__ = ["ModelRecommendation", "RiskFeatures", "deterministic_recurrence_score"]

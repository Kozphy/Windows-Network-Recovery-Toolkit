"""Expose deterministic scoring primitives for the ``python -m src`` CLI tier.

Consumers typically import `score_root_causes` alongside `explain_primary`; lower layers
produce `FeatureVector` inputs upstream.
"""

from .scoring import ALL_CAUSES, DecisionResult, RootCauseKey, explain_primary, score_root_causes

__all__ = ["ALL_CAUSES", "DecisionResult", "RootCauseKey", "explain_primary", "score_root_causes"]

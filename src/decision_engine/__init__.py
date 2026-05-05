"""Expose deterministic v1 FeatureVector scoring primitives for the ``python -m src`` CLI tier.

Implementation lives in :mod:`src.hypothesis.v1_scoring`; this package re-exports for
historical import paths.
"""

from .scoring import ALL_CAUSES, DecisionResult, RootCauseKey, explain_primary, score_root_causes

__all__ = ["ALL_CAUSES", "DecisionResult", "RootCauseKey", "explain_primary", "score_root_causes"]

"""B0: basic reachability-only operational baseline."""

from __future__ import annotations

from typing import Any

from .common import SAFE_LIMITATIONS, Prediction, safe_policy_for_classification


def predict(case: dict[str, Any]) -> Prediction:
    """Map one basic reachability observation to a coarse incident label."""
    reachable = case["signals"].get("connectivity_ok")
    if reachable is True:
        predicted = "NO_PROXY_DIRECT_OK"
        supporting = ("connectivity_ok=true",)
    elif reachable is False:
        predicted = "BOTH_DIRECT_AND_PROXY_FAIL"
        supporting = ("connectivity_ok=false",)
    else:
        predicted = "NOT_ENOUGH_EVIDENCE"
        supporting = ("connectivity_ok=unknown",)
    limitations = SAFE_LIMITATIONS + (
        "Connectivity-only diagnosis cannot distinguish application, proxy, or TLS paths.",
    )
    return Prediction(
        model_or_baseline="B0_connectivity_only",
        predicted_class=predicted,
        proof_tier="T0_OBSERVATION_ONLY",
        limitations=limitations,
        policy_decision=safe_policy_for_classification(predicted),
        supporting_signals=supporting,
        classification_supported=predicted != "NOT_ENOUGH_EVIDENCE",
    )

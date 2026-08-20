"""B2: WinINET configuration-only diagnostic baseline."""

from __future__ import annotations

from typing import Any

from .common import SAFE_LIMITATIONS, Prediction, is_localhost_proxy, safe_policy_for_classification


def predict(case: dict[str, Any]) -> Prediction:
    """Classify using only WinINET enabled/server configuration."""
    signals = case["signals"]
    enabled = signals.get("wininet_proxy_enabled")
    server = signals.get("wininet_proxy_server")
    if enabled is False:
        predicted = "NO_PROXY"
        supporting = ("wininet_proxy_enabled=false",)
        supported = False
    elif enabled is True and is_localhost_proxy(server):
        predicted = "UNKNOWN_LOCAL_PROXY"
        supporting = ("wininet_proxy_enabled=true", "proxy_server=loopback")
        supported = True
    elif enabled is True:
        predicted = "INSUFFICIENT_DATA"
        supporting = ("wininet_proxy_enabled=true", "proxy_server=non_loopback_or_missing")
        supported = False
    else:
        predicted = "NOT_ENOUGH_EVIDENCE"
        supporting = ("wininet_proxy_enabled=unknown",)
        supported = False
    limitations = SAFE_LIMITATIONS + (
        "WinINET configuration alone cannot establish listener or network-path health.",
    )
    return Prediction(
        model_or_baseline="B2_single_signal",
        predicted_class=predicted,
        proof_tier="T0_OBSERVATION_ONLY",
        limitations=limitations,
        policy_decision=safe_policy_for_classification(predicted),
        supporting_signals=supporting,
        classification_supported=supported,
    )

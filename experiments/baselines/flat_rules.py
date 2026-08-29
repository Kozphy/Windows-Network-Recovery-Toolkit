"""B1: credible flat rules without evidence aggregation or proof tiers."""

from __future__ import annotations

from typing import Any

from .common import (
    ABSTENTION_CLASSIFICATIONS,
    SAFE_LIMITATIONS,
    Prediction,
    is_localhost_proxy,
    safe_policy_for_classification,
)


def _flat_classification(signals: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    enabled = signals.get("wininet_proxy_enabled")
    server = signals.get("wininet_proxy_server")
    listener = signals.get("listener_found")
    direct = signals.get("direct_probe_ok")
    proxy = signals.get("proxy_probe_ok")
    status = str(signals.get("proxy_status") or "")

    if signals.get("reverter_suspected"):
        return "REVERTER_SUSPECTED", ("reverter_suspected=true",)
    if enabled is False:
        if direct is False:
            return "BOTH_DIRECT_AND_PROXY_FAIL", ("proxy_disabled", "direct_probe_ok=false")
        if direct is True:
            return "NO_PROXY_DIRECT_OK", ("proxy_disabled", "direct_probe_ok=true")
        return "INSUFFICIENT_DATA", ("proxy_disabled", "direct_probe=unknown")
    if enabled is not True:
        return "INSUFFICIENT_DATA", ("wininet_proxy_enabled=unknown",)
    if server and not is_localhost_proxy(server):
        return "INSUFFICIENT_DATA", ("non_loopback_proxy_configured",)
    if listener is False:
        return "DEAD_PROXY_CONFIG", ("proxy_enabled", "listener_found=false")

    status_map = {
        "DIRECT_ONLY_WORKS": "DIRECT_ONLY_WORKS",
        "BOTH_DIRECT_AND_PROXY_WORK": "BOTH_DIRECT_AND_PROXY_WORK",
        "HEALTHY_LOCALHOST_PROXY": "BOTH_DIRECT_AND_PROXY_WORK",
        "PROXY_ONLY_WORKS": "PROXY_ONLY_WORKS",
        "BOTH_DIRECT_AND_PROXY_FAIL": "BOTH_DIRECT_AND_PROXY_FAIL",
    }
    if status in status_map:
        return status_map[status], (f"proxy_status={status}",)
    if direct is True and proxy is False:
        return "DIRECT_ONLY_WORKS", ("direct_probe_ok=true", "proxy_probe_ok=false")
    if direct is False and proxy is True:
        return "PROXY_ONLY_WORKS", ("direct_probe_ok=false", "proxy_probe_ok=true")
    if direct is False and proxy is False:
        return "BOTH_DIRECT_AND_PROXY_FAIL", (
            "direct_probe_ok=false",
            "proxy_probe_ok=false",
        )
    if signals.get("winhttp_direct_access") is True:
        return "WININET_WINHTTP_MISMATCH", ("wininet_enabled", "winhttp_direct")
    if listener is True:
        return "LOCAL_PROXY_ACTIVE", ("proxy_enabled", "listener_found=true")
    return "UNKNOWN_LOCAL_PROXY", ("proxy_enabled", "listener_state=unknown")


def predict(case: dict[str, Any]) -> Prediction:
    """Apply deterministic first-match rules to all supplied observations."""
    predicted, supporting = _flat_classification(case["signals"])
    limitations = SAFE_LIMITATIONS + (
        "Flat rules do not aggregate contradictions or assign evidence strength.",
    )
    return Prediction(
        model_or_baseline="B1_flat_rules",
        predicted_class=predicted,
        proof_tier="T0_OBSERVATION_ONLY",
        limitations=limitations,
        policy_decision=safe_policy_for_classification(predicted),
        supporting_signals=supporting,
        classification_supported=predicted not in ABSTENTION_CLASSIFICATIONS,
    )

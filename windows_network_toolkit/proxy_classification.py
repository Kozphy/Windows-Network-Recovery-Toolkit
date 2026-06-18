"""Proxy classification facade."""

from __future__ import annotations

from typing import Any

from src.platform_core.attribution.collector import collect_attribution
from src.platform_core.attribution.models import ProcessAttribution, ProxyStateSnapshot
from src.platform_core.classification.engine import classify_proxy
from windows_network_toolkit.models import ClassificationResult
from windows_network_toolkit.proxy_owner import detect_proxy_owner


def classify_from_live(
    *,
    inject: dict[str, Any] | None = None,
    inject_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> ClassificationResult:
    if inject:
        return ClassificationResult(
            primary_classification=str(inject["primary_classification"]),
            secondary_signals=list(inject.get("secondary_signals") or []),
            severity=str(inject.get("severity") or "info"),
            confidence=float(inject.get("confidence") or 0.0),
            reasoning=str(inject.get("reasoning") or ""),
            evidence=list(inject.get("evidence") or []),
            recommended_next_actions=list(inject.get("recommended_next_actions") or []),
            limitations=list(inject.get("limitations") or []),
        )

    snap = collect_attribution(**kwargs)
    owner = detect_proxy_owner(**kwargs)
    listener_detected = bool(owner.get("listener_found"))
    raw = classify_proxy(
        snap.proxy_state,
        snap.listener,
        listener_detected=listener_detected,
        registry_rewrite_observed=bool(kwargs.get("registry_rewrite_observed")),
        writer_listener_mismatch=bool(kwargs.get("writer_listener_mismatch")),
        repeated_reappearance=bool(kwargs.get("repeated_reappearance")),
        reverter_suspected=bool(kwargs.get("reverter_suspected")),
    )
    return ClassificationResult(**raw)


def classify_from_snapshots(
    proxy: ProxyStateSnapshot,
    process: ProcessAttribution,
    *,
    listener_detected: bool = False,
    **flags: Any,
) -> ClassificationResult:
    raw = classify_proxy(proxy, process, listener_detected=listener_detected, **flags)
    return ClassificationResult(**raw)

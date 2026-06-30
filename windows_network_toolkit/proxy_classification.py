"""Proxy classification facade."""

from __future__ import annotations

from typing import Any

from src.platform_core.attribution.collector import collect_attribution
from src.platform_core.attribution.models import ProcessAttribution, ProxyStateSnapshot
from src.platform_core.classification.engine import classify_proxy
from windows_network_toolkit.models import ClassificationResult
from windows_network_toolkit.proxy_health import check_localhost_proxy_health
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
    proxy_health_status: str | None = None
    port = snap.proxy_state.localhost_port
    if snap.proxy_state.wininet_proxy_enable == 1 and port:
        parsed_host = "127.0.0.1"
        health = check_localhost_proxy_health(
            parsed_host,
            int(port),
            listener_info=owner,
            inject=kwargs.get("health_inject"),
            run=kwargs.get("run"),
            run_direct_probe=kwargs.get("run_direct_probe", True),
            run_proxy_probe=kwargs.get("run_proxy_probe", True),
            timeout_seconds=float(kwargs.get("timeout_seconds", 5.0)),
        )
        proxy_health_status = health.proxy_status
    raw = classify_proxy(
        snap.proxy_state,
        snap.listener,
        listener_detected=listener_detected,
        registry_rewrite_observed=bool(kwargs.get("registry_rewrite_observed")),
        writer_listener_mismatch=bool(kwargs.get("writer_listener_mismatch")),
        repeated_reappearance=bool(kwargs.get("repeated_reappearance")),
        reverter_suspected=bool(kwargs.get("reverter_suspected")),
        proxy_health_status=proxy_health_status,
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

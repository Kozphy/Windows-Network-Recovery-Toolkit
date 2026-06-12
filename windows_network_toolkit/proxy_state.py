"""Proxy state collection facade."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from src.platform_core.attribution.collector import collect_proxy_state

from windows_network_toolkit.models import ProxyState


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_proxy_state_model(
    *,
    run: Callable[..., Any] | None = None,
    timeout: float = 15.0,
    inject: dict[str, Any] | None = None,
) -> ProxyState:
    if inject:
        return ProxyState(
            timestamp_utc=str(inject.get("timestamp_utc") or _now()),
            wininet_proxy_enabled=bool(inject.get("wininet_proxy_enabled")),
            wininet_proxy_server=str(inject.get("wininet_proxy_server") or ""),
            wininet_proxy_override=str(inject.get("wininet_proxy_override") or ""),
            wininet_auto_config_url=str(inject.get("wininet_auto_config_url") or ""),
            winhttp_direct_access=bool(inject.get("winhttp_direct_access", True)),
            winhttp_raw_excerpt=str(inject.get("winhttp_raw_excerpt") or ""),
            localhost_port=inject.get("localhost_port"),
            source=str(inject.get("source") or "fixture"),
            errors=list(inject.get("errors") or []),
        )

    run_fn = run or subprocess.run
    errors: list[str] = []
    try:
        snap = collect_proxy_state(run=run_fn, timeout=timeout)
    except Exception as exc:
        return ProxyState(
            timestamp_utc=_now(),
            wininet_proxy_enabled=False,
            wininet_proxy_server="",
            wininet_proxy_override="",
            wininet_auto_config_url="",
            winhttp_direct_access=True,
            winhttp_raw_excerpt="",
            localhost_port=None,
            errors=[str(exc)],
        )

    return ProxyState(
        timestamp_utc=_now(),
        wininet_proxy_enabled=snap.wininet_proxy_enable == 1,
        wininet_proxy_server=snap.wininet_proxy_server,
        wininet_proxy_override=snap.wininet_proxy_override,
        wininet_auto_config_url=snap.wininet_auto_config_url,
        winhttp_direct_access=snap.winhttp_direct_access,
        winhttp_raw_excerpt=snap.winhttp_raw[:400],
        localhost_port=snap.localhost_port,
        errors=errors,
    )

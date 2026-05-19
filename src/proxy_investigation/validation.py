"""Read-only validation probes for investigation runs."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

from ..proxy_guard.connectivity import capture_connectivity_snapshot
from ..proxy_guard.parser import parse_proxy_server
from ..proxy_guard.proxy_path_operational import assess_proxy_path_operational
from ..proxy_guard.registry import read_proxy_registry


def run_validation(
    *,
    run: Callable[..., Any] = subprocess.run,
    timeout_seconds: float = 15.0,
    include_https_contrast: bool = True,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """DNS, TCP 443, HTTPS, and optional proxy path contrast."""
    reg = read_proxy_registry(run=run, query_timeout=timeout_seconds)
    parsed = parse_proxy_server(reg.proxy_server)
    conn = capture_connectivity_snapshot(
        run=run,
        snapshot=None,
        timeout_seconds=timeout_seconds,
    )
    path = assess_proxy_path_operational(
        proxy_enable=reg.proxy_enable,
        proxy_server=reg.proxy_server,
        auto_config_url=reg.auto_config_url,
        parsed=parsed,
        port_listen=None,
        run=run,
        include_https_contrast=include_https_contrast,
        timeout_seconds=timeout_seconds,
    )
    operational = path.operational
    validation = {
        "dns_ok": conn.dns_google.ok,
        "tcp_443_ok": conn.tcp_443_google.ok,
        "https_ok": conn.https_google.ok,
        "https_microsoft_ok": conn.https_microsoft.ok,
        "proxy_bypass_https_ok": operational.get("bypass_https_ok"),
        "proxied_https_ok": operational.get("proxied_https_ok"),
        "connectivity_snapshot": conn.to_jsonable(),
        "limitations": [
            "Probes validate reachability only; they do not prove registry writer identity.",
        ],
    }
    return validation, path.to_jsonable()

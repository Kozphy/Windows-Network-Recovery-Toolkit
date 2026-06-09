"""Netstat / listener collector facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def collect_netstat_signals(
    *,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Capture localhost listen ports and established connection counts."""
    from src.observability.tcp_table import capture_netstat_ano, localhost_listen_ports

    kwargs: dict[str, Any] = {}
    if run is not None:
        kwargs["run"] = run
    code, text = capture_netstat_ano(**kwargs)
    listen_ports = list(localhost_listen_ports(text)) if code == 0 else []
    return {
        "exit_code": code,
        "localhost_listen_ports": listen_ports,
        "raw_line_count": len(text.splitlines()) if text else 0,
        "source": "netstat_ano",
    }

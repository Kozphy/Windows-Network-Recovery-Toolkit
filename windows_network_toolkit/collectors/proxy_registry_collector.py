"""Proxy registry collector facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def collect_proxy_registry(
    *,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Read WinINET user proxy registry state (Windows-only live path)."""
    from src.proxy_guard.registry import read_proxy_registry

    kwargs: dict[str, Any] = {}
    if run is not None:
        kwargs["run"] = run
    snap = read_proxy_registry(**kwargs)
    return {
        "proxy_enable": snap.proxy_enable,
        "proxy_server": snap.proxy_server,
        "auto_config_url": snap.auto_config_url,
        "proxy_override": snap.proxy_override,
        "auto_detect": snap.auto_detect,
        "source": "hkcu_internet_settings",
    }

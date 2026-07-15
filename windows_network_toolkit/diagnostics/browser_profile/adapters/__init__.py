"""Adapter registry."""

from __future__ import annotations

from windows_network_toolkit.diagnostics.browser_profile.adapters.base import BrowserAdapter
from windows_network_toolkit.diagnostics.browser_profile.adapters.chrome import ChromeAdapter
from windows_network_toolkit.diagnostics.browser_profile.adapters.edge import EdgeAdapter


def get_adapter(browser: str) -> BrowserAdapter:
    key = (browser or "auto").lower().strip()
    if key in {"edge", "msedge"}:
        return EdgeAdapter()
    if key in {"chrome", "google-chrome"}:
        return ChromeAdapter()
    if key == "auto":
        edge = EdgeAdapter()
        if edge.detect_installation().get("installed"):
            return edge
        chrome = ChromeAdapter()
        if chrome.detect_installation().get("installed"):
            return chrome
        return edge
    raise ValueError(f"Unsupported browser adapter: {browser}")


__all__ = ["BrowserAdapter", "ChromeAdapter", "EdgeAdapter", "get_adapter"]

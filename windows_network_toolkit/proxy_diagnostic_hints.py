"""Operator hints when proxy classification and symptoms disagree."""

from __future__ import annotations

from typing import Any

_NO_PROXY_HINTS = [
    "If browsers still fail with ERR_PROXY_CONNECTION_FAILED: re-read WinINET registry "
    "(ProxyEnable/ProxyServer) — stale UI or another user profile may differ.",
    "WinHTTP may be direct while WinINET is proxied — compare netsh winhttp show proxy.",
    "Check per-app proxy (IDE, Electron), VPN agents, and HTTP_PROXY/HTTPS_PROXY env vars.",
    "git pull over SSH failing is often missing GitHub SSH keys — not DEAD_PROXY_CONFIG.",
    "Run: python -m windows_network_toolkit proxy-health then proxy-watch for drift evidence.",
]

_DEAD_PROXY_HINTS = [
    "Run proxy-health for path probes, then proxy-watch to capture reverter loops.",
    "Preview fix: python -m windows_network_toolkit proxy-disable --dry-run true",
    "Live apply requires typed confirmation DISABLE_WININET_PROXY (CLI preview-first).",
    "One-shot scripts (auto-fix-proxy.ps1) may live-apply with embedded tokens — see docs/dead-proxy-watch-workflow.md.",
]

_REVERTER_HINTS = [
    "Pattern suggests proxy reverter loop — correlation only, not writer proof.",
    "Run scripts/configure-cursor-no-proxy.ps1; do not auto-kill processes.",
    "Keep proxy-watch read-only until human review.",
]


def build_proxy_status_hints(
    *,
    classification: str,
    payload: dict[str, Any],
    direct_probe_ok: bool | None = None,
) -> list[str]:
    """Build non-accusatory diagnostic hints for proxy-status output."""
    hints: list[str] = []
    primary = str(classification or "").upper()

    if primary == "NO_PROXY":
        hints.extend(_NO_PROXY_HINTS)
        if direct_probe_ok is False:
            hints.insert(
                0,
                "Direct HTTPS probe failed while WinINET shows NO_PROXY — investigate DNS, TLS, or firewall path.",
            )
    elif primary == "DEAD_PROXY_CONFIG":
        hints.extend(_DEAD_PROXY_HINTS)
    elif primary in {"REVERTER_SUSPECTED", "PROXY_FLAPPING"}:
        hints.extend(_REVERTER_HINTS)

    if payload.get("winhttp", {}).get("direct_access") and payload.get("wininet", {}).get("ProxyEnable") == 1:
        hints.append("WinINET/WinHTTP mismatch detected — browsers use WinINET; some CLI tools use WinHTTP.")

    return list(dict.fromkeys(hints))

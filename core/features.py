"""Normalize probe output into the feature schema consumed by ``decision``."""

from __future__ import annotations

from typing import Any, TypedDict


class Features(TypedDict):
    ping_ip_ok: bool
    ping_domain_ok: bool
    nslookup_ok: bool
    tcp_443_ok: bool
    browser_http_ok: bool
    proxy_enabled: bool
    winhttp_proxy_enabled: bool
    dns_servers_detected: int
    adapter_connected: bool
    gateway_reachable: bool | None
    tls_cert_issue_detected: bool
    firewall_path_suspected: bool
    time_wait_count: int
    established_count: int


def from_dict(data: dict[str, Any]) -> Features:
    """Load features from saved JSON or fixture."""

    gw = data.get("gateway_reachable")
    if gw is not None and not isinstance(gw, bool):
        gw = bool(gw)
    f: Features = {
        "ping_ip_ok": bool(data["ping_ip_ok"]),
        "ping_domain_ok": bool(data.get("ping_domain_ok", False)),
        "nslookup_ok": bool(data["nslookup_ok"]),
        "tcp_443_ok": bool(data.get("tcp_443_ok", False)),
        "browser_http_ok": bool(data["browser_http_ok"]),
        "proxy_enabled": bool(data.get("proxy_enabled", False)),
        "winhttp_proxy_enabled": bool(data.get("winhttp_proxy_enabled", False)),
        "dns_servers_detected": int(data.get("dns_servers_detected", 0)),
        "adapter_connected": bool(data.get("adapter_connected", True)),
        "gateway_reachable": gw if gw is None or isinstance(gw, bool) else bool(gw),
        "tls_cert_issue_detected": bool(data.get("tls_cert_issue_detected", False)),
        "firewall_path_suspected": bool(data.get("firewall_path_suspected", False)),
        "time_wait_count": int(data.get("time_wait_count", 0)),
        "established_count": int(data.get("established_count", 0)),
    }
    return f


def to_dict(f: Features) -> dict[str, Any]:
    return dict(f)


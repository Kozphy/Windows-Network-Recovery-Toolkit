"""Structured diagnostic features derived from Windows probes (no secrets)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FeatureVector:
    """Boolean/numeric features used by the decision engine."""

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "ping_ip_ok": self.ping_ip_ok,
            "ping_domain_ok": self.ping_domain_ok,
            "nslookup_ok": self.nslookup_ok,
            "tcp_443_ok": self.tcp_443_ok,
            "browser_http_ok": self.browser_http_ok,
            "proxy_enabled": self.proxy_enabled,
            "winhttp_proxy_enabled": self.winhttp_proxy_enabled,
            "dns_servers_detected": self.dns_servers_detected,
            "adapter_connected": self.adapter_connected,
            "gateway_reachable": self.gateway_reachable,
            "tls_cert_issue_detected": self.tls_cert_issue_detected,
            "firewall_path_suspected": self.firewall_path_suspected,
            "time_wait_count": self.time_wait_count,
            "established_count": self.established_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeatureVector:
        gw = data.get("gateway_reachable")
        if gw is not None and not isinstance(gw, bool):
            gw = bool(gw)
        return cls(
            ping_ip_ok=bool(data["ping_ip_ok"]),
            ping_domain_ok=bool(data.get("ping_domain_ok", False)),
            nslookup_ok=bool(data["nslookup_ok"]),
            tcp_443_ok=bool(data.get("tcp_443_ok", False)),
            browser_http_ok=bool(data["browser_http_ok"]),
            proxy_enabled=bool(data.get("proxy_enabled", False)),
            winhttp_proxy_enabled=bool(data.get("winhttp_proxy_enabled", False)),
            dns_servers_detected=int(data.get("dns_servers_detected", 0)),
            adapter_connected=bool(data.get("adapter_connected", True)),
            gateway_reachable=gw,  # type: ignore[arg-type]
            tls_cert_issue_detected=bool(data.get("tls_cert_issue_detected", False)),
            firewall_path_suspected=bool(data.get("firewall_path_suspected", False)),
            time_wait_count=int(data.get("time_wait_count", 0)),
            established_count=int(data.get("established_count", 0)),
        )

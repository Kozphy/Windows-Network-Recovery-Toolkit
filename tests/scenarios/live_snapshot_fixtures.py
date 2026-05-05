"""Pure factory helpers — no subprocess, stable UTC timestamp for repeatable scoring.

Scenario catalog (for audit / docs parity with ``test_decision_*`` modules):

┌─────────────────────────────┬────────────────────────────────────────────────────────────┐
│ live.dns_failure            │ Ping OK to IP, resolver failure → dns_resolution_issue high │
│ live.tcp443_blocked          │ ICMP+DNS OK, TCP 443+HTTPS probe fail → Winsock/stack priors │
│ live.https_tls_failure       │ TCP 443 OK, curl HTTPS fail + TLS heuristic → tls_path_issue │
│ live.conflicting_stack       │ Many layers unhealthy → stacked winsock + multiple highs   │
│ live.localhost_proxy_benign  │ HKCU loopback proxy ON, transport OK → unexpected_user_proxy│
└─────────────────────────────┴────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from src.core.models import LiveNetworkSnapshot, PortOwnerRecord, ProxyRegistrySnapshot
from src.diagnostics.features import FeatureVector
from src.proxy_guard.parser import parse_proxy_server


def _fv(**overrides: bool | int | None) -> FeatureVector:
    base: dict[str, bool | int | None] = {
        "ping_ip_ok": True,
        "ping_domain_ok": True,
        "nslookup_ok": True,
        "tcp_443_ok": True,
        "browser_http_ok": True,
        "proxy_enabled": False,
        "winhttp_proxy_enabled": False,
        "dns_servers_detected": 2,
        "adapter_connected": True,
        "gateway_reachable": True,
        "tls_cert_issue_detected": False,
        "firewall_path_suspected": False,
        "time_wait_count": 20,
        "established_count": 20,
    }
    base.update(overrides)
    return FeatureVector(**base)


def snapshot_from(
    fv: FeatureVector,
    *,
    proxy_enable: int = 0,
    proxy_server: str | None = None,
    auto_detect: int = 0,
) -> LiveNetworkSnapshot:
    """Build frozen :class:`LiveNetworkSnapshot` with parsed ProxyServer-derived fields."""
    reg = ProxyRegistrySnapshot(
        proxy_enable=proxy_enable,
        proxy_server=proxy_server,
        auto_config_url=None,
        auto_detect=auto_detect,
    )
    parsed = parse_proxy_server(reg.proxy_server)
    return LiveNetworkSnapshot(
        generated_at_utc="2026-05-05T12:00:00Z",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parsed,
        port_owners=(),
        localhost_listen_ports=(),
        interesting_processes=(),
        tcp_top_ports=(),
        commands_executed=(),
        permission_notes=(),
    )


def scenario_dns_failure() -> LiveNetworkSnapshot:
    fv = _fv(nslookup_ok=False)
    return snapshot_from(fv)


def scenario_tcp443_blocked() -> LiveNetworkSnapshot:
    fv = _fv(tcp_443_ok=False, browser_http_ok=False)
    return snapshot_from(fv)


def scenario_https_tls_failure() -> LiveNetworkSnapshot:
    fv = _fv(
        tcp_443_ok=True,
        browser_http_ok=False,
        tls_cert_issue_detected=True,
    )
    return snapshot_from(fv)


def scenario_conflicting_signals() -> LiveNetworkSnapshot:
    """ICMP up but WAN IP path down, resolver down, transports down — overlapping failure families."""
    fv = _fv(
        ping_domain_ok=False,
        nslookup_ok=False,
        ping_ip_ok=True,
        tcp_443_ok=False,
        browser_http_ok=False,
        gateway_reachable=True,
        winhttp_proxy_enabled=True,
    )
    reg = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:8888",
        auto_config_url=None,
        auto_detect=0,
    )
    parsed = parse_proxy_server(reg.proxy_server)
    return LiveNetworkSnapshot(
        generated_at_utc="2026-05-05T12:00:00Z",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parsed,
        port_owners=(),
        localhost_listen_ports=(),
        interesting_processes=(),
        tcp_top_ports=(),
        commands_executed=(),
        permission_notes=("fixture:conflicting_signals",),
    )


def scenario_localhost_proxy_benign() -> LiveNetworkSnapshot:
    """Loopback ProxyServer enabled; synthetic transport healthy → unexpected_user_proxy dominates."""
    fv = _fv(
        proxy_enabled=True,
        ping_ip_ok=True,
        ping_domain_ok=True,
        nslookup_ok=True,
        tcp_443_ok=True,
        browser_http_ok=True,
    )
    reg = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:9999",
        auto_config_url=None,
        auto_detect=0,
    )
    parsed = parse_proxy_server(reg.proxy_server)
    assert parsed.is_localhost_proxy
    return LiveNetworkSnapshot(
        generated_at_utc="2026-05-05T12:00:00Z",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parsed,
        port_owners=(
            PortOwnerRecord(
                port=9999,
                pid=4242,
                process_name="testproxy.exe",
                state="LISTEN",
                local_address="127.0.0.1:9999",
                parent_pid=None,
                parent_name=None,
                command_line=None,
                executable_path=None,
                permission_limited=False,
            ),
        ),
        localhost_listen_ports=(9999,),
        interesting_processes=(),
        tcp_top_ports=(),
        commands_executed=(),
        permission_notes=(),
    )

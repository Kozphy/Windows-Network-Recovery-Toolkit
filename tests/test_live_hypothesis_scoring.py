from __future__ import annotations

from src.core.models import LiveNetworkSnapshot, ParsedProxy, PortOwnerRecord, ProxyRegistrySnapshot
from src.decision_engine.live_scoring import score_live_snapshot
from src.diagnostics.features import FeatureVector
from src.proxy_guard.parser import parse_proxy_server


def _fx(**kwargs: object) -> FeatureVector:
    base = FeatureVector.from_dict(
        {
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
            "time_wait_count": 0,
            "established_count": 0,
        }
    )
    d = base.to_dict()
    d.update(kwargs)
    return FeatureVector.from_dict(d)


def test_unexpected_user_proxy_ranks_first() -> None:
    fv = _fx(browser_http_ok=True, tcp_443_ok=True, nslookup_ok=True, proxy_enabled=True)
    reg = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:58815",
        auto_config_url=None,
        auto_detect=0,
    )
    parsed = parse_proxy_server(reg.proxy_server)
    owner = (
        PortOwnerRecord(
            port=58815,
            pid=24040,
            process_name="node.exe",
            state="Listen",
            local_address=None,
            parent_pid=7580,
            parent_name="powershell.exe",
            command_line=None,
            executable_path=None,
            permission_limited=True,
        ),
    )
    snap = LiveNetworkSnapshot(
        generated_at_utc="stub",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parsed,
        port_owners=owner,
        commands_executed=(),
    )
    ranked = score_live_snapshot(snap)
    assert ranked[0].hypothesis == "unexpected_user_proxy"
    assert ranked[0].confidence >= 0.8


def test_dns_issue_surfaces_when_nslookup_fails() -> None:
    fv = _fx(
        ping_ip_ok=True,
        ping_domain_ok=False,
        nslookup_ok=False,
        tcp_443_ok=False,
        browser_http_ok=False,
    )
    reg = ProxyRegistrySnapshot(
        proxy_enable=0,
        proxy_server=None,
        auto_config_url=None,
        auto_detect=None,
    )
    snap = LiveNetworkSnapshot(
        generated_at_utc="stub",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parse_proxy_server(None),
        commands_executed=(),
    )
    ranked = score_live_snapshot(snap)
    hypotheses = [s.hypothesis for s in ranked[:5]]
    assert "dns_resolution_issue" in hypotheses

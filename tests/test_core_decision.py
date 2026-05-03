"""Deterministic decision rules (no subprocess)."""

from __future__ import annotations

from pathlib import Path

from core import decision
from core.features import Features


def test_dns_pattern_high_confidence() -> None:
    # IP OK, nslookup fail — classic DNS signal
    f: Features = {
        "ping_ip_ok": True,
        "ping_domain_ok": False,
        "nslookup_ok": False,
        "tcp_443_ok": True,
        "browser_http_ok": True,
        "proxy_enabled": False,
        "winhttp_proxy_enabled": False,
        "dns_servers_detected": 1,
        "adapter_connected": True,
        "gateway_reachable": True,
        "tls_cert_issue_detected": False,
        "firewall_path_suspected": False,
        "time_wait_count": 0,
        "established_count": 0,
    }
    r = decision.score(f)
    assert r["primary"]["issue"] == "dns_issue"
    assert float(r["primary"]["confidence"]) >= 0.7
    assert "reason" in r["primary"]


def test_proxy_https_fail() -> None:
    f: Features = {
        "ping_ip_ok": True,
        "ping_domain_ok": True,
        "nslookup_ok": True,
        "tcp_443_ok": True,
        "browser_http_ok": False,
        "proxy_enabled": True,
        "winhttp_proxy_enabled": True,
        "dns_servers_detected": 1,
        "adapter_connected": True,
        "gateway_reachable": True,
        "tls_cert_issue_detected": False,
        "firewall_path_suspected": True,
        "time_wait_count": 0,
        "established_count": 0,
    }
    r = decision.score(f)
    assert r["primary"]["issue"] == "proxy_issue"


def test_actions_mapping() -> None:
    from core.actions import suggestions

    rows = suggestions("dns_issue", {"time_wait_count": 0, "established_count": 0})
    assert any(r.get("script") and "reset_dns.bat" in str(r["script"]) for r in rows)


def test_fixture_roundtrip(tmp_path: Path) -> None:
    from core import probes

    p = tmp_path / "f.json"
    p.write_text(
        '{"ping_ip_ok": true, "ping_domain_ok": false, "nslookup_ok": false, '
        '"tcp_443_ok": true, "browser_http_ok": true, "proxy_enabled": false, '
        '"winhttp_proxy_enabled": false, "dns_servers_detected": 1, '
        '"adapter_connected": true, "gateway_reachable": true, '
        '"tls_cert_issue_detected": false, "firewall_path_suspected": false, '
        '"time_wait_count": 0, "established_count": 0}',
        encoding="utf-8",
    )
    feats = probes.load_fixture(p)
    assert decision.score(feats)["primary"]["issue"] == "dns_issue"

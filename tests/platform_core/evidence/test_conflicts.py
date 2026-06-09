"""Evidence conflict detection tests."""

from __future__ import annotations

from src.platform_core.evidence.conflicts import detect_conflicts


def test_dns_ok_http_fail() -> None:
    c = detect_conflicts({"dns_ok": True, "browser_https_failed": True})
    assert any(x.code == "DNS_OK_HTTP_FAIL" for x in c)


def test_listener_no_writer() -> None:
    c = detect_conflicts({"listener_on_proxy_port": True})
    assert any(x.code == "LISTENER_NO_WRITER_PROOF" for x in c)

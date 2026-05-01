from __future__ import annotations

from src.proxy_guard.parser import parse_proxy_server, summarize_proxy_risk


def test_parse_plain_localhost_ipv4() -> None:
    p = parse_proxy_server("127.0.0.1:58815")
    assert p.proxy_mode == "manual_localhost"
    assert p.is_localhost_proxy
    assert p.localhost_port == 58815


def test_parse_plain_localhost_name() -> None:
    p = parse_proxy_server("localhost:8080")
    assert p.is_localhost_proxy
    assert p.localhost_port == 8080


def test_parse_http_https_pair() -> None:
    raw = "http=127.0.0.1:50347;https=127.0.0.1:50347"
    p = parse_proxy_server(raw)
    assert p.proxy_mode == "http_https_localhost"
    assert p.is_localhost_proxy
    assert p.http_localhost_port == 50347
    assert p.https_localhost_port == 50347


def test_parse_socks_localhost() -> None:
    p = parse_proxy_server("socks=127.0.0.1:7890")
    assert p.proxy_mode == "socks_localhost"
    assert p.socks_port == 7890


def test_empty_means_missing() -> None:
    assert parse_proxy_server("").is_missing
    assert parse_proxy_server("   ").is_missing


def test_malformed_random() -> None:
    assert parse_proxy_server("http=").is_malformed


def test_risk_label() -> None:
    p = parse_proxy_server("127.0.0.1:1")
    assert summarize_proxy_risk(p, proxy_enable_is_on=True) == "high"
    assert summarize_proxy_risk(p, proxy_enable_is_on=False) == "low"

"""Unit tests for proxy attribution (mocked; no live Windows registry required)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from proxy_attribution.classifier import classify_proxy_source, recommended_action_and_risk
from proxy_attribution.port_mapper import parse_local_proxy_server


def test_parse_local_proxy() -> None:
    h, p = parse_local_proxy_server("127.0.0.1:50347")
    assert h == "127.0.0.1"
    assert p == 50347


def test_classify_vpn_client() -> None:
    c, conf, _ = classify_proxy_source(
        process_name="Clash for Windows.exe",
        proxy_signal_active=True,
        proxy_server="127.0.0.1:7890",
        localhost_port_mapped=True,
    )
    assert c == "vpn_client"
    assert conf >= 0.9


def test_classify_enterprise_no_process() -> None:
    c, conf, _ = classify_proxy_source(
        process_name=None,
        proxy_signal_active=True,
        proxy_server="proxy.corp.example:8080",
        localhost_port_mapped=False,
    )
    assert c == "enterprise_policy"
    assert conf < 0.5


def test_recommended_action_mapping() -> None:
    a, r = recommended_action_and_risk("vpn_client")
    assert a == "disable_proxy"
    assert r == "low"


@patch("proxy_attribution.attribution_engine._process_auto_start_hints", return_value=False)
@patch("proxy_attribution.attribution_engine.collect_proxy_snapshot")
@patch("proxy_attribution.attribution_engine.map_local_proxy_port")
def test_run_attribution_smoke(
    mock_map: object,
    mock_snap: object,
    _mock_hints: object,
) -> None:
    from proxy_attribution.attribution_engine import run_attribution

    mock_snap.return_value = SimpleNamespace(
        proxy_enabled=True,
        proxy_server="127.0.0.1:7890",
        auto_config_url=None,
        wininet_proxy_enable=1,
        winhttp_raw="",
        winhttp_direct=True,
        winhttp_proxy_line=None,
        winhttp_summary="DIRECT",
    )
    mock_map.return_value = {
        "port": 7890,
        "process_name": "clash-win.exe",
        "pid": 4242,
        "listening_state": "LISTENING",
        "local_address": "127.0.0.1:7890",
    }

    out = run_attribution()
    assert out["classification"] == "vpn_client"
    assert out["recommended_action"] == "disable_proxy"
    assert "explanation" in out

"""Parametrized classification matrix tests."""

from __future__ import annotations

import pytest

from src.platform_core.attribution.models import ProcessAttribution, ProxyStateSnapshot
from src.platform_core.classification.engine import classify_proxy
from src.platform_core.classification.models import PrimaryClassification


@pytest.mark.parametrize(
    "proxy,process,listener,flags,expected_primary,min_conf,max_conf",
    [
        (
            ProxyStateSnapshot(wininet_proxy_enable=0),
            ProcessAttribution(),
            False,
            {},
            PrimaryClassification.NO_PROXY,
            0.9,
            1.0,
        ),
        (
            ProxyStateSnapshot(
                wininet_proxy_enable=1,
                wininet_proxy_server="127.0.0.1:59081",
                localhost_port=59081,
                winhttp_direct_access=True,
            ),
            ProcessAttribution(),
            False,
            {},
            PrimaryClassification.DEAD_PROXY_CONFIG,
            0.85,
            1.0,
        ),
        (
            ProxyStateSnapshot(
                wininet_proxy_enable=1,
                wininet_proxy_server="127.0.0.1:8080",
                localhost_port=8080,
            ),
            ProcessAttribution(pid=1, process_name="node.exe"),
            True,
            {},
            PrimaryClassification.KNOWN_DEV_PROXY,
            0.7,
            1.0,
        ),
        (
            ProxyStateSnapshot(
                wininet_proxy_enable=1,
                wininet_proxy_server="127.0.0.1:8888",
                localhost_port=8888,
            ),
            ProcessAttribution(pid=2, process_name="zscaler.exe"),
            True,
            {},
            PrimaryClassification.KNOWN_SECURITY_TOOL,
            0.7,
            1.0,
        ),
        (
            ProxyStateSnapshot(
                wininet_proxy_enable=1,
                wininet_proxy_server="127.0.0.1:9999",
                localhost_port=9999,
            ),
            ProcessAttribution(pid=3, process_name="unknown.exe"),
            True,
            {},
            PrimaryClassification.UNKNOWN_LOCAL_PROXY,
            0.4,
            0.7,
        ),
        (
            ProxyStateSnapshot(wininet_auto_config_url="http://pac.example/proxy.pac"),
            ProcessAttribution(),
            False,
            {},
            PrimaryClassification.PAC_CONFIGURED,
            0.6,
            1.0,
        ),
        (
            ProxyStateSnapshot(
                wininet_proxy_enable=1,
                wininet_proxy_server="203.0.113.50:8080",
                winhttp_direct_access=True,
            ),
            ProcessAttribution(),
            False,
            {},
            PrimaryClassification.POSSIBLE_MITM_RISK,
            0.3,
            0.6,
        ),
        (
            None,
            None,
            False,
            {"insufficient_data": True},
            PrimaryClassification.ERROR_INSUFFICIENT_DATA,
            0.0,
            0.3,
        ),
        (
            ProxyStateSnapshot(
                wininet_proxy_enable=1,
                wininet_proxy_server="127.0.0.1:7777",
                localhost_port=7777,
            ),
            ProcessAttribution(pid=4, process_name="evil.exe", command_line="mitm-proxy"),
            True,
            {},
            PrimaryClassification.SUSPICIOUS_PROXY,
            0.5,
            0.8,
        ),
        (
            ProxyStateSnapshot(wininet_proxy_enable=0),
            ProcessAttribution(),
            False,
            {"reverter_suspected": True, "repeated_reappearance": True},
            PrimaryClassification.REVERTER_SUSPECTED,
            0.7,
            0.9,
        ),
    ],
)
def test_classification_matrix(
    proxy,
    process,
    listener,
    flags,
    expected_primary,
    min_conf,
    max_conf,
) -> None:
    result = classify_proxy(
        proxy,
        process,
        listener_detected=listener,
        **flags,
    )
    assert result["primary_classification"] == expected_primary.value
    assert min_conf <= result["confidence"] <= max_conf
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["limitations"]


def test_dead_proxy_has_mismatch_signal() -> None:
    proxy = ProxyStateSnapshot(
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:59081",
        localhost_port=59081,
        winhttp_direct_access=True,
    )
    result = classify_proxy(proxy, ProcessAttribution(), listener_detected=False)
    assert "WININET_WINHTTP_MISMATCH" in result["secondary_signals"]
    assert "DEAD_LOCALHOST_PORT" in result["secondary_signals"]

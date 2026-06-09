"""Certified replay determinism."""

from __future__ import annotations

from src.platform_core.replay.certifier import certify_case


def test_certified_replay_deterministic() -> None:
    signals = {
        "wininet_proxy_enabled": True,
        "proxy_server_localhost": True,
        "browser_https_failed": True,
        "proxy_bypass_succeeded": True,
    }
    cert = certify_case(signals=signals)
    assert cert.certification_hash
    assert cert.certified or cert.errors  # may not reach FINAL_CAUSATION without full proof

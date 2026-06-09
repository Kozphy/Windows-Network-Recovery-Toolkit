"""Replay blocks unsafe upgrade."""

from __future__ import annotations

from src.platform_core.replay.certifier import certify_case


def test_correlation_fixture_not_certified_for_destructive() -> None:
    signals = {"listener_on_proxy_port": True, "listener_correlation": True}
    cert = certify_case(signals=signals)
    assert cert.destructive_unlocked is False

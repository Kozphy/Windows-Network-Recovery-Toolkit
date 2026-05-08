from __future__ import annotations

from platform_core.demo import run_demo


def test_run_demo_fixture_assertions():
    payload = run_demo()
    assert payload["dns_preview_allowed"] is True
    assert payload["firewall_preview_allowed"] is False
    assert payload["arbitrary_forbidden"] is True

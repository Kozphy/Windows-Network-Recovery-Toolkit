from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.decision_platform import AdapterContext, PlatformDomain, get_adapter, list_domains
from platform_core.decision_platform.adapters import (
    CloudAdapter,
    InfrastructureAdapter,
    MarketAdapter,
    SecurityAdapter,
    WindowsAdapter,
)


@pytest.mark.parametrize(
    ("domain", "adapter_cls"),
    [
        (PlatformDomain.WINDOWS, WindowsAdapter),
        (PlatformDomain.SECURITY, SecurityAdapter),
        (PlatformDomain.CLOUD, CloudAdapter),
        (PlatformDomain.INFRASTRUCTURE, InfrastructureAdapter),
        (PlatformDomain.MARKET_EVENTS, MarketAdapter),
    ],
)
def test_registry_resolves_all_domains(domain: PlatformDomain, adapter_cls: type) -> None:
    adapter = get_adapter(domain)
    assert isinstance(adapter, adapter_cls)
    assert adapter.domain == domain


def test_list_domains_complete() -> None:
    assert set(list_domains()) == {d.value for d in PlatformDomain}


def test_windows_pipeline_output_contract() -> None:
    result = WindowsAdapter().evaluate(AdapterContext(payload={"proxy_enabled": True}))
    assert result.domain == "windows"
    assert len(result.observations) >= 2
    assert len(result.evidence) >= 1
    assert result.decision.title
    assert 0.0 <= result.decision.confidence <= 1.0
    assert len(result.engine_digest) == 64


def test_market_adapter_uses_calendar_fixture() -> None:
    root = Path(__file__).resolve().parents[2]
    cal = root / "fixtures" / "market_events" / "calendar.json"
    result = MarketAdapter().evaluate(
        AdapterContext(payload={"event_id": "CPI_2026_06"}, fixture_path=str(cal))
    )
    assert result.domain == "market_events"
    assert any("CPI_2026_06" in str(obs.value) for obs in result.observations)


def test_shared_engine_deterministic_across_domains() -> None:
    ctx = AdapterContext(payload={})
    digest_a = get_adapter(PlatformDomain.SECURITY).evaluate(ctx).engine_digest
    digest_b = get_adapter(PlatformDomain.SECURITY).evaluate(ctx).engine_digest
    assert digest_a == digest_b


def test_all_domains_produce_decision() -> None:
    for domain in PlatformDomain:
        result = get_adapter(domain).evaluate(AdapterContext(payload={}))
        assert result.decision.domain == domain.value
        assert result.decision.final_score >= 0

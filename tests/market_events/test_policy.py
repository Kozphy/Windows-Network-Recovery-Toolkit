from __future__ import annotations

from pathlib import Path

from src.market_events.calendar import get_event
from src.market_events.models import EventCategory, MarketEvent, ResearchPolicyStatus
from src.market_events.policy import evaluate_research_policy


def test_low_confidence_block() -> None:
    event = MarketEvent(
        event_id="LOW_CONF_TEST",
        title="Low confidence with source",
        category=EventCategory.MACRO,
        timestamp_utc="2026-06-01T00:00:00Z",
        affected_assets=["BTC"],
        confidence=0.35,
        source="fixture:test",
    )
    status = evaluate_research_policy(event, request_execution=False)
    assert status == ResearchPolicyStatus.BLOCK_LOW_CONFIDENCE


def test_preview_only_no_source(calendar_fixture: Path) -> None:
    event = get_event("BRIDGE_EXPLOIT_2026_06", calendar_fixture)
    status = evaluate_research_policy(event, request_execution=False)
    assert status == ResearchPolicyStatus.PREVIEW_ONLY


def test_block_trade_execution(calendar_fixture: Path) -> None:
    event = get_event("CPI_2026_06", calendar_fixture)
    status = evaluate_research_policy(event, request_execution=True)
    assert status == ResearchPolicyStatus.BLOCK_TRADE_EXECUTION


def test_allow_research_healthy_event(calendar_fixture: Path) -> None:
    event = get_event("CPI_2026_06", calendar_fixture)
    status = evaluate_research_policy(event, request_execution=False)
    assert status == ResearchPolicyStatus.ALLOW_RESEARCH

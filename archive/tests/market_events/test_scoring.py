from __future__ import annotations

from pathlib import Path

from src.market_events.calendar import get_event
from src.market_events.scoring import score_event


def test_macro_btc_increases_volatility(calendar_fixture: Path) -> None:
    event = get_event("CPI_2026_06", calendar_fixture)
    score = score_event(event)
    assert score.volatility_score >= 60
    assert score.confidence > 0.4
    assert any("macro" in d.lower() or "BTC" in d for d in score.main_drivers)


def test_token_unlock_bearish_direction(calendar_fixture: Path) -> None:
    event = get_event("ARB_UNLOCK_2026_06", calendar_fixture)
    score = score_event(event)
    assert score.direction_score < 0
    assert any("unlock" in d.lower() or "supply" in d.lower() for d in score.main_drivers)


def test_etf_flow_bullish(calendar_fixture: Path) -> None:
    event = get_event("BTC_ETF_INFLOW_2026_06", calendar_fixture)
    score = score_event(event)
    assert score.direction_score > 0


def test_security_incident_high_volatility(calendar_fixture: Path) -> None:
    event = get_event("BRIDGE_EXPLOIT_2026_06", calendar_fixture)
    score = score_event(event)
    assert score.volatility_score >= 50
    assert score.direction_score < 0

"""MVP event detection."""

from __future__ import annotations

import pytest

from trading_research.events.detector import DetectorConfig, detect_events
from trading_research.events.event_types import EventType, MarketEvent


def test_only_mvp_event_types_detected(minimal_ohlcv) -> None:
    events = detect_events(minimal_ohlcv, symbol="TEST", config=DetectorConfig(breakout_lookback=5))
    for ev in events:
        assert ev.event_type in {EventType.PRICE_BREAKOUT, EventType.VOLUME_SPIKE}


def test_confidence_ordinal_rejects_float() -> None:
    with pytest.raises(ValueError):
        MarketEvent(
            timestamp="2024-01-01T00:00:00Z",
            event_type=EventType.VOLUME_SPIKE,
            symbol="X",
            evidence="test",
            confidence_score="INVALID",
        )

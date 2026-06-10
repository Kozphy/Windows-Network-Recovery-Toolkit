"""MVP signal generation — confluence required."""

from __future__ import annotations

from trading_research.events.event_types import EventType, MarketEvent
from trading_research.signals.generator import generate_signals
from trading_research.signals.signal import SignalDirection


def test_breakout_alone_no_signal() -> None:
    events = [
        MarketEvent(
            timestamp="2024-01-10T00:00:00Z",
            event_type=EventType.PRICE_BREAKOUT,
            symbol="SPY",
            evidence="breakout",
            confidence_score="MEDIUM",
        )
    ]
    assert generate_signals(events) == []


def test_volume_spike_alone_no_signal() -> None:
    events = [
        MarketEvent(
            timestamp="2024-01-10T00:00:00Z",
            event_type=EventType.VOLUME_SPIKE,
            symbol="SPY",
            evidence="spike",
            confidence_score="HIGH",
        )
    ]
    assert generate_signals(events) == []


def test_confluence_generates_long() -> None:
    ts = "2024-01-10T00:00:00Z"
    events = [
        MarketEvent(
            timestamp=ts,
            event_type=EventType.PRICE_BREAKOUT,
            symbol="SPY",
            evidence="breakout",
            confidence_score="MEDIUM",
        ),
        MarketEvent(
            timestamp=ts,
            event_type=EventType.VOLUME_SPIKE,
            symbol="SPY",
            evidence="spike",
            confidence_score="HIGH",
        ),
    ]
    signals = generate_signals(events)
    assert len(signals) == 1
    assert signals[0].direction == SignalDirection.LONG
    assert signals[0].source_event == "PRICE_BREAKOUT+VOLUME_SPIKE"


def test_different_timestamps_no_signal() -> None:
    events = [
        MarketEvent(
            timestamp="2024-01-10T00:00:00Z",
            event_type=EventType.PRICE_BREAKOUT,
            symbol="SPY",
            evidence="breakout",
            confidence_score="MEDIUM",
        ),
        MarketEvent(
            timestamp="2024-01-11T00:00:00Z",
            event_type=EventType.VOLUME_SPIKE,
            symbol="SPY",
            evidence="spike",
            confidence_score="HIGH",
        ),
    ]
    assert generate_signals(events) == []

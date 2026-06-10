"""MVP signal rules — LONG only when PRICE_BREAKOUT and VOLUME_SPIKE share a timestamp."""

from __future__ import annotations

from collections import defaultdict

from trading_research.events.event_types import EventType, MarketEvent

from .signal import SignalDirection, TradingSignal


def generate_signals(events: list[MarketEvent]) -> list[TradingSignal]:
    """Emit LONG candidate only on same-timestamp breakout + volume spike confluence."""
    by_ts: dict[str, list[MarketEvent]] = defaultdict(list)
    for ev in events:
        by_ts[ev.timestamp].append(ev)

    signals: list[TradingSignal] = []
    for ts in sorted(by_ts.keys()):
        day_events = by_ts[ts]
        types = {e.event_type for e in day_events}
        if EventType.PRICE_BREAKOUT not in types or EventType.VOLUME_SPIKE not in types:
            continue
        breakout = next(e for e in day_events if e.event_type == EventType.PRICE_BREAKOUT)
        spike = next(e for e in day_events if e.event_type == EventType.VOLUME_SPIKE)
        confidence = "HIGH" if breakout.confidence_score == "HIGH" or spike.confidence_score == "HIGH" else "MEDIUM"
        signals.append(
            TradingSignal(
                timestamp=ts,
                symbol=day_events[0].symbol,
                direction=SignalDirection.LONG,
                source_event="PRICE_BREAKOUT+VOLUME_SPIKE",
                rationale=(
                    "Breakout and volume spike at same timestamp — "
                    "candidate LONG (signal != edge)."
                ),
                confidence_score=confidence,
                invalidation_rule="Exit next bar if confluence does not persist.",
            )
        )
    return signals

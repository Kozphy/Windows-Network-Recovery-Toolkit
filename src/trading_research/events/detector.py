"""MVP event detectors — PRICE_BREAKOUT and VOLUME_SPIKE only."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .event_types import EventType, MarketEvent


@dataclass(frozen=True)
class DetectorConfig:
    breakout_lookback: int = 20
    volume_lookback: int = 20
    volume_spike_multiplier: float = 2.0


def _price_breakout(df: pd.DataFrame, i: int, lookback: int) -> MarketEvent | None:
    if i < lookback:
        return None
    window = df.iloc[i - lookback : i]
    prior_high = float(window["high"].max())
    close = float(df.iloc[i]["close"])
    if close > prior_high:
        return MarketEvent(
            timestamp=str(df.iloc[i]["timestamp"]),
            event_type=EventType.PRICE_BREAKOUT,
            symbol=str(df.attrs.get("symbol", "UNKNOWN")),
            evidence=f"close {close:.4f} > {lookback}-bar high {prior_high:.4f}",
            confidence_score="MEDIUM",
            metadata={"lookback": lookback, "prior_high": prior_high, "close": close},
        )
    return None


def _volume_spike(df: pd.DataFrame, i: int, lookback: int, mult: float) -> MarketEvent | None:
    if i < lookback:
        return None
    window = df.iloc[i - lookback : i]
    mean_vol = float(window["volume"].mean())
    vol = float(df.iloc[i]["volume"])
    if mean_vol > 0 and vol >= mean_vol * mult:
        return MarketEvent(
            timestamp=str(df.iloc[i]["timestamp"]),
            event_type=EventType.VOLUME_SPIKE,
            symbol=str(df.attrs.get("symbol", "UNKNOWN")),
            evidence=f"volume {vol:.0f} >= {mult}x rolling mean {mean_vol:.0f}",
            confidence_score="HIGH" if vol >= mean_vol * (mult + 0.5) else "MEDIUM",
            metadata={"volume": vol, "rolling_mean": mean_vol, "multiplier": mult},
        )
    return None


def detect_events(
    df: pd.DataFrame,
    *,
    symbol: str,
    config: DetectorConfig | None = None,
) -> list[MarketEvent]:
    """Scan OHLCV series; windows use only past bars (no look-ahead)."""
    cfg = config or DetectorConfig()
    work = df.copy()
    work.attrs["symbol"] = symbol
    events: list[MarketEvent] = []
    for i in range(len(work)):
        breakout = _price_breakout(work, i, cfg.breakout_lookback)
        if breakout is not None:
            events.append(breakout)
        spike = _volume_spike(work, i, cfg.volume_lookback, cfg.volume_spike_multiplier)
        if spike is not None:
            events.append(spike)
    return events

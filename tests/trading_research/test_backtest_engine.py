"""MVP backtest — next-bar, long-only."""

from __future__ import annotations

from trading_research.backtest.engine import BacktestConfig, run_backtest
from trading_research.signals.signal import SignalDirection, TradingSignal


def _long_signal(ts: str) -> TradingSignal:
    return TradingSignal(
        timestamp=ts,
        symbol="TEST",
        direction=SignalDirection.LONG,
        source_event="PRICE_BREAKOUT+VOLUME_SPIKE",
        rationale="test",
        confidence_score="MEDIUM",
    )


def test_next_bar_execution(minimal_ohlcv) -> None:
    ts = minimal_ohlcv.iloc[10]["timestamp"]
    result = run_backtest(minimal_ohlcv, [_long_signal(ts)], config=BacktestConfig(initial_capital=10_000))
    assert float(result.positions.iloc[10]) == 0.0
    assert float(result.positions.iloc[11]) == 1.0


def test_no_lookahead(minimal_ohlcv) -> None:
    from trading_research.events.detector import DetectorConfig, detect_events

    cfg = DetectorConfig(breakout_lookback=5, volume_lookback=5, volume_spike_multiplier=2.0)
    events_a = detect_events(minimal_ohlcv, symbol="T", config=cfg)
    df_trimmed = minimal_ohlcv.iloc[:-1].copy()
    events_b = detect_events(df_trimmed, symbol="T", config=cfg)
    ts = minimal_ohlcv.iloc[-2]["timestamp"]
    types_a = {e.event_type for e in events_a if e.timestamp == ts}
    types_b = {e.event_type for e in events_b if e.timestamp == ts}
    assert types_a == types_b


def test_metrics_populated(minimal_ohlcv) -> None:
    ts = minimal_ohlcv.iloc[25]["timestamp"]
    result = run_backtest(minimal_ohlcv, [_long_signal(ts)])
    assert "total_return" in result.metrics
    assert "sharpe_ratio" in result.metrics
    assert "max_drawdown" in result.metrics
    assert "number_of_trades" in result.metrics

"""Market data loading and validation."""

from __future__ import annotations

import pytest

from trading_research.data.market_data import MarketDataError, load_ohlcv_csv


def test_load_sample_csv(sample_csv_path) -> None:
    df, meta = load_ohlcv_csv(sample_csv_path, symbol="SPY")
    assert len(df) > 0
    assert meta.symbol == "SPY"
    assert meta.start_timestamp <= meta.end_timestamp
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


def test_missing_columns(tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("timestamp,close\n2024-01-01,100\n", encoding="utf-8")
    with pytest.raises(MarketDataError, match="Missing required columns"):
        load_ohlcv_csv(bad)


def test_sorted_timestamps(sample_csv_path) -> None:
    df, _ = load_ohlcv_csv(sample_csv_path)
    assert df["timestamp"].is_monotonic_increasing

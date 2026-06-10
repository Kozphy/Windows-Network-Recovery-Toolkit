"""Fixtures for MVP trading research tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

SAMPLE_CSV = (
    Path(__file__).resolve().parents[2] / "src" / "trading_research" / "examples" / "sample_ohlcv.csv"
)


@pytest.fixture
def sample_csv_path() -> Path:
    return SAMPLE_CSV


@pytest.fixture
def minimal_ohlcv() -> pd.DataFrame:
    """Series with one confluence bar (breakout + volume spike at index 25)."""
    start = datetime(2024, 1, 2)
    rows = []
    for i in range(40):
        close = 100.0 + i * 0.1
        volume = 1_000_000
        if i == 25:
            close = 120.0
            volume = 3_500_000
        ts = (start + timedelta(days=i)).strftime("%Y-%m-%dT00:00:00Z")
        rows.append(
            {
                "timestamp": ts,
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": volume,
            }
        )
    return pd.DataFrame(rows)

"""OHLCV data schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


class OhlcvBar(BaseModel):
    """Single normalized OHLCV bar."""

    timestamp: str
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class MarketDataMeta(BaseModel):
    """Metadata for a loaded price series."""

    symbol: str
    row_count: int
    start_timestamp: str
    end_timestamp: str
    source_path: str = ""
    data_hash: str = ""

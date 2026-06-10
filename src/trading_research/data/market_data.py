"""Load and validate OHLCV market data from CSV."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .schema import REQUIRED_COLUMNS, MarketDataMeta


class MarketDataError(ValueError):
    """Raised when CSV data fails validation."""


def _canonical_rows_hash(df: pd.DataFrame) -> str:
    payload = df[["timestamp", "open", "high", "low", "close", "volume"]].to_dict(orient="records")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_ohlcv_csv(
    path: str | Path,
    *,
    symbol: str = "UNKNOWN",
) -> tuple[pd.DataFrame, MarketDataMeta]:
    """Load OHLCV CSV, validate columns, normalize timestamps, sort ascending."""
    p = Path(path)
    if not p.is_file():
        raise MarketDataError(f"Data file not found: {p}")

    df = pd.read_csv(p)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise MarketDataError(f"Missing required columns: {missing}")

    df = df[list(REQUIRED_COLUMNS)].copy()
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if ts.isna().any():
        raise MarketDataError("Invalid timestamp values in data file")

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise MarketDataError("Non-numeric OHLCV values detected")

    if (df["high"] < df["low"]).any():
        raise MarketDataError("high < low detected")
    if (df["close"] > df["high"]).any() or (df["close"] < df["low"]).any():
        raise MarketDataError("close outside high/low range")
    if (df["open"] > df["high"]).any() or (df["open"] < df["low"]).any():
        raise MarketDataError("open outside high/low range")

    df["timestamp"] = ts
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    meta = MarketDataMeta(
        symbol=symbol,
        row_count=len(df),
        start_timestamp=str(df["timestamp"].iloc[0]),
        end_timestamp=str(df["timestamp"].iloc[-1]),
        source_path=str(p.resolve()),
        data_hash=_canonical_rows_hash(df),
    )
    return df, meta

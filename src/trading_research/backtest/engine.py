"""MVP backtest — next-bar execution, long-only, no leverage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from trading_research.signals.signal import TradingSignal

from .metrics import compute_metrics


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    transaction_cost_bps: float = 5.0
    periods_per_year: int = 252


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, Any]


def run_backtest(
    df: pd.DataFrame,
    signals: list[TradingSignal],
    *,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Execute LONG signals on next bar open; flat when no signal."""
    cfg = config or BacktestConfig()
    n = len(df)
    if n == 0:
        empty = pd.Series(dtype=float)
        return BacktestResult(
            equity_curve=empty,
            returns=empty,
            positions=empty,
            trades=pd.DataFrame(columns=["entry_idx", "exit_idx", "return"]),
            metrics=compute_metrics(empty, pd.DataFrame()),
        )

    signal_ts = {s.timestamp for s in signals}
    timestamps = list(df["timestamp"])

    desired = pd.Series(0.0, index=range(n))
    for i, ts in enumerate(timestamps):
        if ts in signal_ts:
            desired.iloc[i] = 1.0

    position = pd.Series(0.0, index=range(n))
    for i in range(n - 1):
        position.iloc[i + 1] = desired.iloc[i]

    cost_rate = cfg.transaction_cost_bps / 10_000.0
    price = df["open"].astype(float)
    bar_returns = price.pct_change().fillna(0.0)
    position_change = position.diff().fillna(position.iloc[0]).abs()
    strategy_returns = position * bar_returns - position_change * cost_rate

    equity = cfg.initial_capital * (1.0 + strategy_returns).cumprod()
    equity.index = df["timestamp"]

    trades_rows: list[dict[str, Any]] = []
    in_trade = False
    entry_idx = 0
    entry_equity = cfg.initial_capital
    for i in range(1, n):
        prev_pos = float(position.iloc[i - 1])
        cur_pos = float(position.iloc[i])
        if not in_trade and prev_pos == 0.0 and cur_pos != 0.0:
            in_trade = True
            entry_idx = i
            entry_equity = float(equity.iloc[i - 1])
        elif in_trade and cur_pos == 0.0:
            exit_equity = float(equity.iloc[i])
            trades_rows.append(
                {
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "entry_timestamp": timestamps[entry_idx],
                    "exit_timestamp": timestamps[i],
                    "return": exit_equity / entry_equity - 1.0,
                }
            )
            in_trade = False

    trades = pd.DataFrame(trades_rows)
    metrics = compute_metrics(equity, trades, periods_per_year=cfg.periods_per_year)

    return BacktestResult(
        equity_curve=equity,
        returns=strategy_returns,
        positions=position,
        trades=trades,
        metrics=metrics,
    )

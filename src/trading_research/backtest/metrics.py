"""MVP backtest metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def compute_metrics(
    equity_curve: pd.Series,
    trades: pd.DataFrame,
    *,
    periods_per_year: int = 252,
) -> dict[str, Any]:
    """Return total return, Sharpe, max drawdown, and trade count."""
    if equity_curve.empty:
        return {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "number_of_trades": 0,
        }

    returns = equity_curve.pct_change().dropna()
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0)
    n = max(len(returns), 1)
    ann_factor = periods_per_year / n
    annualized_return = float((1.0 + total_return) ** ann_factor - 1.0)
    volatility = float(returns.std() * np.sqrt(periods_per_year)) if len(returns) > 1 else 0.0
    sharpe = float(annualized_return / volatility) if volatility > 1e-12 else 0.0

    rolling_max = equity_curve.cummax()
    drawdown = equity_curve / rolling_max - 1.0
    max_drawdown = float(drawdown.min())

    return {
        "total_return": round(total_return, 6),
        "sharpe_ratio": round(sharpe, 6),
        "max_drawdown": round(max_drawdown, 6),
        "number_of_trades": int(len(trades)),
    }

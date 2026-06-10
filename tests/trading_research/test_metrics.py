"""MVP metrics."""

from __future__ import annotations

import pandas as pd

from trading_research.backtest.metrics import compute_metrics


def test_mvp_metrics_keys() -> None:
    equity = pd.Series([100.0, 101.0, 99.0, 102.0])
    trades = pd.DataFrame({"return": [0.01, -0.02]})
    m = compute_metrics(equity, trades)
    assert set(m.keys()) == {"total_return", "sharpe_ratio", "max_drawdown", "number_of_trades"}
    assert m["number_of_trades"] == 2

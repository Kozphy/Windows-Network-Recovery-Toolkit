"""Risk rule definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_drawdown_limit: float = -0.25
    min_number_of_trades: int = 5
    max_turnover: float = 50.0
    min_sharpe: float = 0.5
    max_single_trade_loss: float = -0.10


RISK_RULE_IDS = (
    "max_drawdown_limit",
    "min_number_of_trades",
    "max_turnover",
    "min_sharpe",
    "max_single_trade_loss",
)

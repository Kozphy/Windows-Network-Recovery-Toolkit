"""Strategy risk evaluation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from .rules import RiskLimits


class RiskVerdict(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class RiskEvaluation(BaseModel):
    verdict: RiskVerdict
    reasons: list[str] = Field(default_factory=list)
    violated_rules: list[str] = Field(default_factory=list)
    recommended_action: str = ""


def evaluate_risk(
    metrics: dict[str, Any],
    trades: pd.DataFrame,
    positions: pd.Series,
    *,
    limits: RiskLimits | None = None,
) -> RiskEvaluation:
    """Evaluate backtest metrics against risk limits."""
    lim = limits or RiskLimits()
    reasons: list[str] = []
    violated: list[str] = []
    fail_count = 0
    warn_count = 0

    mdd = float(metrics.get("max_drawdown", 0.0))
    if mdd < lim.max_drawdown_limit:
        violated.append("max_drawdown_limit")
        reasons.append(f"Max drawdown {mdd:.2%} below limit {lim.max_drawdown_limit:.2%}")
        fail_count += 1

    n_trades = int(metrics.get("number_of_trades", 0))
    if n_trades < lim.min_number_of_trades:
        violated.append("min_number_of_trades")
        reasons.append(f"Only {n_trades} trades; minimum sample is {lim.min_number_of_trades}")
        warn_count += 1

    turnover = float(positions.diff().abs().sum()) if len(positions) else 0.0
    if turnover > lim.max_turnover:
        violated.append("max_turnover")
        reasons.append(f"Turnover {turnover:.1f} exceeds limit {lim.max_turnover:.1f}")
        warn_count += 1

    sharpe = float(metrics.get("sharpe_ratio", 0.0))
    if sharpe < lim.min_sharpe:
        violated.append("min_sharpe")
        reasons.append(f"Sharpe {sharpe:.2f} below minimum {lim.min_sharpe:.2f}")
        warn_count += 1

    if not trades.empty and "return" in trades.columns:
        worst = float(trades["return"].min())
        if worst < lim.max_single_trade_loss:
            violated.append("max_single_trade_loss")
            reasons.append(f"Worst trade {worst:.2%} exceeds loss limit {lim.max_single_trade_loss:.2%}")
            fail_count += 1

    if fail_count > 0:
        verdict = RiskVerdict.FAIL
        action = "Do not advance to paper trading; refine hypothesis or gather more data."
    elif warn_count > 0:
        verdict = RiskVerdict.WARN
        action = "Continue research only; address warnings before paper trading."
    else:
        verdict = RiskVerdict.PASS
        action = "Risk checks passed for research stage; policy gate still required."

    return RiskEvaluation(
        verdict=verdict,
        reasons=reasons,
        violated_rules=violated,
        recommended_action=action,
    )

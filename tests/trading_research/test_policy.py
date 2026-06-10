"""MVP policy gate."""

from __future__ import annotations

from trading_research.policy.gate import apply_policy
from trading_research.policy.policy_schema import PolicyDecision


def test_needs_more_data_below_20_trades() -> None:
    result = apply_policy({"number_of_trades": 5, "max_drawdown": -0.05, "sharpe_ratio": 1.0})
    assert result.decision == PolicyDecision.NEEDS_MORE_DATA


def test_block_on_drawdown() -> None:
    result = apply_policy({"number_of_trades": 25, "max_drawdown": -0.25, "sharpe_ratio": 1.0})
    assert result.decision == PolicyDecision.BLOCK


def test_approve_research_only() -> None:
    result = apply_policy({"number_of_trades": 25, "max_drawdown": -0.10, "sharpe_ratio": 0.8})
    assert result.decision == PolicyDecision.APPROVE_RESEARCH_ONLY

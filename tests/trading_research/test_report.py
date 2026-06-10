"""MVP report export."""

from __future__ import annotations

from trading_research.policy.policy_schema import PolicyDecision, PolicyResult
from trading_research.reports.research_report import generate_research_report


def test_report_sections() -> None:
    md = generate_research_report(
        strategy_name="breakout_v1",
        symbol="SPY",
        data_meta={"row_count": 80, "start_timestamp": "a", "end_timestamp": "b"},
        metrics={"total_return": 0.05, "sharpe_ratio": 0.5, "max_drawdown": -0.08, "number_of_trades": 3},
        policy=PolicyResult(
            decision=PolicyDecision.NEEDS_MORE_DATA,
            rationale="insufficient sample",
        ),
        event_count=10,
        signal_count=3,
    )
    assert "Trading Research Report (MVP)" in md
    assert "not financial advice" in md.lower()
    assert "Policy Decision" in md
    assert "confluence LONG" in md

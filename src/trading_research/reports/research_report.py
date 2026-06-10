"""MVP markdown research report."""

from __future__ import annotations

import json
from typing import Any

from trading_research.policy.policy_schema import PolicyResult


def generate_research_report(
    *,
    strategy_name: str,
    symbol: str,
    data_meta: dict[str, Any],
    metrics: dict[str, Any],
    policy: PolicyResult,
    event_count: int,
    signal_count: int,
) -> str:
    """Export markdown report (not financial advice)."""
    lines = [
        "# Trading Research Report (MVP)",
        "",
        f"**Strategy:** {strategy_name}",
        f"**Symbol:** {symbol}",
        "",
        "**Disclaimer:** Research infrastructure only — not financial advice. "
        "Not a trading bot. No live execution.",
        "",
        "## Pipeline",
        "OHLCV CSV → PRICE_BREAKOUT + VOLUME_SPIKE → confluence LONG → "
        "next-bar backtest → policy gate → report",
        "",
        "## Data",
        f"- Rows: {data_meta.get('row_count', 'n/a')}",
        f"- Range: {data_meta.get('start_timestamp')} → {data_meta.get('end_timestamp')}",
        "",
        "## Events & Signals",
        "- Events detected: PRICE_BREAKOUT, VOLUME_SPIKE",
        "- LONG signal only when both occur at the same timestamp",
        f"- Events found: {event_count}",
        f"- Signals generated: {signal_count}",
        "",
        "## Backtest Assumptions",
        "- Execution: next-bar open",
        "- Long-only, no leverage, no short selling",
        "- Transaction cost: 5 bps per position change",
        "",
        "## Metrics",
        "```json",
        json.dumps(metrics, indent=2),
        "```",
        "",
        "## Policy Decision",
        f"- **{policy.decision.value}**",
        f"- {policy.rationale}",
        "",
        "## Limitations",
        "- Observation != signal; signal != edge; backtest != proof",
        "- MVP scope: no ML, no broker API, no live trading",
    ]
    return "\n".join(lines)

"""MVP policy gate — three deterministic rules."""

from __future__ import annotations

from typing import Any

from .policy_schema import PolicyDecision, PolicyResult

MIN_TRADES = 20
MAX_DRAWDOWN_LIMIT = -0.20


def apply_policy(metrics: dict[str, Any]) -> PolicyResult:
    """Apply MVP promotion rules (research only — never live trading)."""
    n_trades = int(metrics.get("number_of_trades", 0))
    if n_trades < MIN_TRADES:
        return PolicyResult(
            decision=PolicyDecision.NEEDS_MORE_DATA,
            rationale=f"Sample size {n_trades} < minimum {MIN_TRADES} trades.",
            blocked_reasons=["insufficient_sample"],
        )

    mdd = float(metrics.get("max_drawdown", 0.0))
    if mdd < MAX_DRAWDOWN_LIMIT:
        return PolicyResult(
            decision=PolicyDecision.BLOCK,
            rationale=f"Max drawdown {mdd:.2%} exceeds limit {MAX_DRAWDOWN_LIMIT:.0%}.",
            blocked_reasons=["max_drawdown_limit"],
        )

    return PolicyResult(
        decision=PolicyDecision.APPROVE_RESEARCH_ONLY,
        rationale="Sample and drawdown within MVP thresholds; continue research only.",
        blocked_reasons=[],
    )

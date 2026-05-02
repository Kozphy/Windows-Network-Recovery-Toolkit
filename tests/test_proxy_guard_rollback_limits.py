from __future__ import annotations

from src.proxy_guard.config import RollbackLimitSettings
from src.proxy_guard.rollback_limits import RollbackLimiter


def test_cooldown_blocks_rapid_rollbacks() -> None:
    mark = [1000.0]

    def clk() -> float:
        return mark[0]

    limiter = RollbackLimiter(
        RollbackLimitSettings(cooldown_seconds=50.0, window_seconds=300.0, max_rollbacks_per_window=99),
        _clock=clk,
    )
    assert limiter.evaluate()[0] is True
    limiter.record_rollback()
    mark[0] = 1001.0
    ok, reason = limiter.evaluate()
    assert ok is False
    assert "rollback_cooldown_active" in reason


def test_window_rate_limit() -> None:
    t = [0.0]

    def clk() -> float:
        return t[0]

    limiter = RollbackLimiter(
        RollbackLimitSettings(cooldown_seconds=0.0, window_seconds=100.0, max_rollbacks_per_window=2),
        _clock=clk,
    )
    assert limiter.evaluate()[0] is True
    limiter.record_rollback()
    t[0] = 1.0
    assert limiter.evaluate()[0] is True
    limiter.record_rollback()
    t[0] = 2.0
    ok, reason = limiter.evaluate()
    assert ok is False
    assert "rollback_rate_limited_in_window" in reason

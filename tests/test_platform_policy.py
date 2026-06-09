"""Unified platform policy engine."""

from __future__ import annotations

from src.platform.models import DecisionOption, NormalizedEvent
from src.platform.policy_engine import evaluate_policy


def test_blocks_destructive() -> None:
    ev = NormalizedEvent(
        event_id="x",
        domain="security",
        category="t",
        title="t",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        source="fixture",
    )
    dec = DecisionOption(
        decision_id="d1",
        event_id="x",
        title="kill process on host",
        action_type="execute_like",
        expected_benefit=0.9,
        risk_score=0.8,
    )
    pol = evaluate_policy(ev, dec, confidence=0.9)
    assert pol.status == "BLOCK_DESTRUCTIVE_ACTION"
    assert pol.execute_allowed is False


def test_blocks_low_confidence() -> None:
    ev = NormalizedEvent(
        event_id="x",
        domain="cloud",
        category="t",
        title="t",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        source="fixture",
    )
    dec = DecisionOption(
        decision_id="d2",
        event_id="x",
        title="research logs",
        action_type="research",
    )
    pol = evaluate_policy(ev, dec, confidence=0.3)
    assert pol.status == "BLOCK_LOW_CONFIDENCE"

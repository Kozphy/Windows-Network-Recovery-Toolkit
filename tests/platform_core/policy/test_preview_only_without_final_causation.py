"""Preview only without final causation."""

from __future__ import annotations

from src.platform_core.contracts import Decision, EvidenceBundle
from src.platform_core.policy.engine import evaluate_policy


def test_blocks_destructive_on_observed_only() -> None:
    decision = Decision(
        decision_id="d1",
        incident_id="i1",
        timestamp_utc="2026-01-01T00:00:00Z",
        incident_type="UNKNOWN",
        recommended_action="DISABLE",
        confidence=0.5,
        evidence_tier="OBSERVED_ONLY",
    )
    bundle = EvidenceBundle(
        bundle_id="b1",
        incident_id="i1",
        created_at="2026-01-01T00:00:00Z",
        tier="OBSERVED_ONLY",
    )
    pe = evaluate_policy(decision=decision, bundle=bundle, requested_action="disable_wininet_proxy")
    assert pe.outcome == "BLOCK"

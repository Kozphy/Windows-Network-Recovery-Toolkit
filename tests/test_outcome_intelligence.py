from __future__ import annotations

import pytest

from windows_network_toolkit.outcome_analytics import summarize_outcomes
from windows_network_toolkit.outcome_schema import (
    OutcomeStatus,
    OutcomeVerification,
    build_outcome_event,
    make_outcome_id,
)


def test_outcome_id_is_deterministic_for_retry_safe_ingestion() -> None:
    kwargs = {
        "incident_id": "inc-59081",
        "observed_at_utc": "2026-07-30T00:00:00Z",
        "status": OutcomeStatus.RESTORED.value,
        "verification": OutcomeVerification.PATH_PROBE_VERIFIED.value,
        "stable_fields": {"endpoint_id": "host-1", "evidence_event_ids": ["e2", "e1"]},
    }
    assert make_outcome_id(**kwargs) == make_outcome_id(**kwargs)


def test_outcome_recurrence_invariant_rejects_inconsistent_data() -> None:
    with pytest.raises(ValueError, match="recurrence_count must be positive"):
        build_outcome_event(
            incident_id="inc-1",
            endpoint_id="host-1",
            observed_at_utc="2026-07-30T00:00:00Z",
            status=OutcomeStatus.RESTORED,
            recurred=True,
            recurrence_count=0,
        )


def test_outcome_metrics_keep_verified_recovery_separate() -> None:
    events = [
        build_outcome_event(
            incident_id="inc-1",
            endpoint_id="host-1",
            observed_at_utc="2026-07-30T00:05:00Z",
            restored_at_utc="2026-07-30T00:05:00Z",
            status=OutcomeStatus.RESTORED,
            verification=OutcomeVerification.PATH_PROBE_VERIFIED,
            time_to_recovery_seconds=300,
            evidence_event_ids=["probe-1"],
        ),
        build_outcome_event(
            incident_id="inc-2",
            endpoint_id="host-2",
            observed_at_utc="2026-07-30T00:10:00Z",
            restored_at_utc="2026-07-30T00:10:00Z",
            status=OutcomeStatus.PARTIALLY_RESTORED,
            verification=OutcomeVerification.OPERATOR_REPORTED,
            time_to_recovery_seconds=900,
            recurred=True,
            recurrence_count=1,
        ),
        build_outcome_event(
            incident_id="inc-3",
            endpoint_id="host-3",
            observed_at_utc="2026-07-30T00:15:00Z",
            status=OutcomeStatus.NOT_RESTORED,
            verification=OutcomeVerification.NOT_VERIFIED,
            rollback_performed=True,
        ),
    ]

    metrics = summarize_outcomes(events)

    assert metrics.total_outcomes == 3
    assert metrics.restored_outcomes == 2
    assert metrics.verified_restored_outcomes == 1
    assert metrics.unresolved_outcomes == 1
    assert metrics.median_time_to_recovery_seconds == 600.0
    assert metrics.restoration_rate == 0.6667
    assert metrics.verified_restoration_rate == 0.5
    assert metrics.recurrence_rate == 0.3333
    assert metrics.rollback_rate == 0.3333
    assert any("do not prove" in item for item in metrics.limitations)


def test_outcome_does_not_require_action_lineage() -> None:
    event = build_outcome_event(
        incident_id="inc-natural-recovery",
        endpoint_id="host-1",
        observed_at_utc="2026-07-30T00:20:00Z",
        status=OutcomeStatus.RESTORED,
        verification=OutcomeVerification.PATH_PROBE_VERIFIED,
        evidence_event_ids=["probe-after-recovery"],
    )

    assert event.action_id is None
    assert event.decision_id is None
    assert "does not by itself prove" in event.limitations[0]

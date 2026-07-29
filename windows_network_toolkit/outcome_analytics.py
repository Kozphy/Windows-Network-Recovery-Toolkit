"""Deterministic outcome metrics for reliability and governance reporting."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from statistics import median
from typing import Iterable

from .outcome_schema import OutcomeEvent, OutcomeStatus, OutcomeVerification


@dataclass(frozen=True)
class OutcomeMetrics:
    total_outcomes: int
    restored_outcomes: int
    verified_restored_outcomes: int
    unresolved_outcomes: int
    recurrent_outcomes: int
    rollback_outcomes: int
    median_time_to_recovery_seconds: float | None
    restoration_rate: float | None
    verified_restoration_rate: float | None
    recurrence_rate: float | None
    rollback_rate: float | None
    status_counts: dict[str, int]
    verification_counts: dict[str, int]
    limitations: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def summarize_outcomes(events: Iterable[OutcomeEvent]) -> OutcomeMetrics:
    """Aggregate outcome rows without interpreting association as causation.

    Rates are descriptive portfolio metrics. They are not calibrated probabilities,
    formal control attestations, or evidence that remediation caused recovery.
    """

    rows = list(events)
    status_counts = Counter(row.status for row in rows)
    verification_counts = Counter(row.verification for row in rows)

    restored_statuses = {
        OutcomeStatus.RESTORED.value,
        OutcomeStatus.PARTIALLY_RESTORED.value,
    }
    unresolved_statuses = {
        OutcomeStatus.OPEN.value,
        OutcomeStatus.NOT_RESTORED.value,
        OutcomeStatus.UNKNOWN.value,
    }
    verified_methods = {
        OutcomeVerification.PATH_PROBE_VERIFIED.value,
        OutcomeVerification.REPLAY_VERIFIED.value,
    }

    restored = [row for row in rows if row.status in restored_statuses]
    verified_restored = [row for row in restored if row.verification in verified_methods]
    unresolved = [row for row in rows if row.status in unresolved_statuses]
    recurrent = [row for row in rows if row.recurred]
    rolled_back = [row for row in rows if row.rollback_performed or row.status == OutcomeStatus.ROLLED_BACK.value]
    recovery_times = [
        row.time_to_recovery_seconds
        for row in restored
        if row.time_to_recovery_seconds is not None
    ]

    limitations = [
        "Metrics are descriptive and do not prove that an action caused an outcome.",
        "Restoration rate includes partial restoration; inspect status counts for detail.",
        "Verification rate only treats path-probe and deterministic replay evidence as verified.",
        "Recurrence rate depends on the available monitoring window and data completeness.",
    ]

    return OutcomeMetrics(
        total_outcomes=len(rows),
        restored_outcomes=len(restored),
        verified_restored_outcomes=len(verified_restored),
        unresolved_outcomes=len(unresolved),
        recurrent_outcomes=len(recurrent),
        rollback_outcomes=len(rolled_back),
        median_time_to_recovery_seconds=float(median(recovery_times)) if recovery_times else None,
        restoration_rate=_rate(len(restored), len(rows)),
        verified_restoration_rate=_rate(len(verified_restored), len(restored)),
        recurrence_rate=_rate(len(recurrent), len(rows)),
        rollback_rate=_rate(len(rolled_back), len(rows)),
        status_counts=dict(sorted(status_counts.items())),
        verification_counts=dict(sorted(verification_counts.items())),
        limitations=limitations,
    )

"""Incident outcome lifecycle for measurable reliability and control effectiveness.

This module closes the evidence-to-outcome loop without changing remediation policy.
Outcome rows describe what happened after a reviewed decision or action; they do not
prove causation, authorize execution, or upgrade an evidence tier.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class OutcomeStatus(StrEnum):
    OPEN = "OPEN"
    RESTORED = "RESTORED"
    PARTIALLY_RESTORED = "PARTIALLY_RESTORED"
    NOT_RESTORED = "NOT_RESTORED"
    ROLLED_BACK = "ROLLED_BACK"
    UNKNOWN = "UNKNOWN"


class OutcomeVerification(StrEnum):
    NOT_VERIFIED = "NOT_VERIFIED"
    OPERATOR_REPORTED = "OPERATOR_REPORTED"
    PATH_PROBE_VERIFIED = "PATH_PROBE_VERIFIED"
    REPLAY_VERIFIED = "REPLAY_VERIFIED"


OUTCOME_LIMITATIONS = [
    "Outcome timing does not by itself prove that an action caused recovery.",
    "Operator-reported recovery requires independent path evidence for stronger verification.",
    "Recurrence is only observable within the configured monitoring window.",
    "Outcome records do not authorize remediation or attest control effectiveness.",
]


@dataclass(frozen=True)
class OutcomeEvent:
    """Immutable, append-oriented incident outcome record.

    ``incident_id`` links the result to the original classified incident. Optional
    decision and action identifiers preserve lineage without requiring an action to
    exist: an endpoint may recover naturally or through an external operator workflow.
    """

    outcome_id: str
    incident_id: str
    endpoint_id: str | None
    observed_at_utc: str
    status: str
    verification: str
    restored_at_utc: str | None = None
    time_to_recovery_seconds: int | None = None
    recurred: bool = False
    recurrence_count: int = 0
    rollback_performed: bool = False
    decision_id: str | None = None
    action_id: str | None = None
    evidence_event_ids: list[str] = field(default_factory=list)
    notes: str = ""
    limitations: list[str] = field(default_factory=lambda: list(OUTCOME_LIMITATIONS))
    schema_version: str = "outcome_event.v1"

    def __post_init__(self) -> None:
        if not self.incident_id.strip():
            raise ValueError("incident_id is required")
        if self.time_to_recovery_seconds is not None and self.time_to_recovery_seconds < 0:
            raise ValueError("time_to_recovery_seconds cannot be negative")
        if self.recurrence_count < 0:
            raise ValueError("recurrence_count cannot be negative")
        if self.recurred and self.recurrence_count == 0:
            raise ValueError("recurrence_count must be positive when recurred is true")
        if not self.recurred and self.recurrence_count != 0:
            raise ValueError("recurrence_count must be zero when recurred is false")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_outcome_id(
    *,
    incident_id: str,
    observed_at_utc: str,
    status: str,
    verification: str,
    stable_fields: dict[str, Any] | None = None,
) -> str:
    """Return a deterministic identifier suitable for retry-safe ingestion."""

    payload = {
        "incident_id": incident_id,
        "observed_at_utc": observed_at_utc,
        "status": status,
        "verification": verification,
        "stable": stable_fields or {},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


def build_outcome_event(
    *,
    incident_id: str,
    endpoint_id: str | None,
    observed_at_utc: str,
    status: OutcomeStatus,
    verification: OutcomeVerification = OutcomeVerification.NOT_VERIFIED,
    restored_at_utc: str | None = None,
    time_to_recovery_seconds: int | None = None,
    recurred: bool = False,
    recurrence_count: int = 0,
    rollback_performed: bool = False,
    decision_id: str | None = None,
    action_id: str | None = None,
    evidence_event_ids: list[str] | None = None,
    notes: str = "",
    limitations: list[str] | None = None,
) -> OutcomeEvent:
    """Construct a validated outcome event with deterministic lineage identity."""

    stable = {
        "endpoint_id": endpoint_id,
        "restored_at_utc": restored_at_utc,
        "decision_id": decision_id,
        "action_id": action_id,
        "evidence_event_ids": sorted(evidence_event_ids or []),
    }
    return OutcomeEvent(
        outcome_id=make_outcome_id(
            incident_id=incident_id,
            observed_at_utc=observed_at_utc,
            status=status.value,
            verification=verification.value,
            stable_fields=stable,
        ),
        incident_id=incident_id,
        endpoint_id=endpoint_id,
        observed_at_utc=observed_at_utc,
        status=status.value,
        verification=verification.value,
        restored_at_utc=restored_at_utc,
        time_to_recovery_seconds=time_to_recovery_seconds,
        recurred=recurred,
        recurrence_count=recurrence_count,
        rollback_performed=rollback_performed,
        decision_id=decision_id,
        action_id=action_id,
        evidence_event_ids=list(evidence_event_ids or []),
        notes=notes,
        limitations=list(limitations) if limitations is not None else list(OUTCOME_LIMITATIONS),
    )


def outcomes_from_dicts(rows: list[dict[str, Any]]) -> list[OutcomeEvent]:
    """Load schema-compatible rows while rejecting silently malformed lifecycle data."""

    fields = OutcomeEvent.__dataclass_fields__
    return [OutcomeEvent(**{key: value for key, value in row.items() if key in fields}) for row in rows]

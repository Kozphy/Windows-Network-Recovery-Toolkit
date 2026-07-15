"""Immutable timing models — urgency, SLA, windows; not execution authorization.

A valid maintenance window is not execution authorization.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_TIMING = "timing_context.v1"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TimingDecision(StrEnum):
    READY = "READY"
    ESCALATE_NOW = "ESCALATE_NOW"
    MONITOR_UNTIL = "MONITOR_UNTIL"
    DEFERRED_TO_WINDOW = "DEFERRED_TO_WINDOW"
    BLOCKED_BY_CHANGE_FREEZE = "BLOCKED_BY_CHANGE_FREEZE"
    EVIDENCE_EXPIRED = "EVIDENCE_EXPIRED"
    SLA_OVERDUE = "SLA_OVERDUE"


class TimingReasonCode(StrEnum):
    WITHIN_SLA = "WITHIN_SLA"
    SLA_BREACHED = "SLA_BREACHED"
    EVIDENCE_VALID = "EVIDENCE_VALID"
    EVIDENCE_STALE = "EVIDENCE_STALE"
    IN_MAINTENANCE_WINDOW = "IN_MAINTENANCE_WINDOW"
    OUTSIDE_MAINTENANCE_WINDOW = "OUTSIDE_MAINTENANCE_WINDOW"
    CHANGE_FREEZE_ACTIVE = "CHANGE_FREEZE_ACTIVE"
    BUSINESS_HOURS = "BUSINESS_HOURS"
    AFTER_HOURS = "AFTER_HOURS"
    HIGH_URGENCY_ESCALATION = "HIGH_URGENCY_ESCALATION"
    RETRY_AFTER_SET = "RETRY_AFTER_SET"


class TimingContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_TIMING
    case_id: str = ""
    detected_at_utc: str
    evaluated_at_utc: str
    timezone: str
    clock_source: str = "UTC"
    urgency: Urgency = Urgency.MEDIUM
    action_window_start_utc: str | None = None
    action_window_end_utc: str | None = None
    sla_due_utc: str | None = None
    evidence_expires_utc: str | None = None
    retry_after_utc: str | None = None
    maintenance_window_required: bool = False
    in_maintenance_window: bool | None = None
    change_freeze_active: bool = False
    business_hours: bool | None = None
    decision: TimingDecision = TimingDecision.READY
    reason_codes: tuple[TimingReasonCode, ...] = ()
    limitations: tuple[str, ...] = (
        "A valid maintenance window is not execution authorization.",
        "High urgency never bypasses typed confirmation.",
        "Timezone must be supplied explicitly; platform core defaults to UTC.",
    )
    inputs_fingerprint: str = ""
    config_refs: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


BusinessHoursSpec = dict[str, Any]  # documented in windows.py

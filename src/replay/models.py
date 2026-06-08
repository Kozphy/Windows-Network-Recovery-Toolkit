"""Timeline replay models — Step 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProxyTimelineEventType(str, Enum):
    PROCESS_CREATED = "PROCESS_CREATED"
    REGISTRY_VALUE_SET = "REGISTRY_VALUE_SET"
    PROXY_STATE_CHANGED = "PROXY_STATE_CHANGED"
    LOCALHOST_LISTENER_OBSERVED = "LOCALHOST_LISTENER_OBSERVED"
    NETWORK_FAILURE_OBSERVED = "NETWORK_FAILURE_OBSERVED"
    CLASSIFICATION_ASSIGNED = "CLASSIFICATION_ASSIGNED"
    POLICY_DECISION_CREATED = "POLICY_DECISION_CREATED"
    REMEDIATION_PREVIEWED = "REMEDIATION_PREVIEWED"
    USER_CONFIRMATION_REQUIRED = "USER_CONFIRMATION_REQUIRED"
    PROXY_DISABLED_CONFIRMED = "PROXY_DISABLED_CONFIRMED"
    UNKNOWN = "UNKNOWN"


_KIND_ORDER: dict[str, int] = {
    ProxyTimelineEventType.PROCESS_CREATED.value: 10,
    ProxyTimelineEventType.REGISTRY_VALUE_SET.value: 20,
    ProxyTimelineEventType.LOCALHOST_LISTENER_OBSERVED.value: 30,
    ProxyTimelineEventType.PROXY_STATE_CHANGED.value: 40,
    ProxyTimelineEventType.CLASSIFICATION_ASSIGNED.value: 50,
    ProxyTimelineEventType.POLICY_DECISION_CREATED.value: 60,
    ProxyTimelineEventType.NETWORK_FAILURE_OBSERVED.value: 70,
    ProxyTimelineEventType.REMEDIATION_PREVIEWED.value: 80,
    ProxyTimelineEventType.USER_CONFIRMATION_REQUIRED.value: 90,
    ProxyTimelineEventType.PROXY_DISABLED_CONFIRMED.value: 100,
    ProxyTimelineEventType.UNKNOWN.value: 99,
}


@dataclass
class ProxyTimelineEvent:
    timestamp_utc: str
    event_type: ProxyTimelineEventType
    source: str
    title: str
    details: str = ""
    process_guid: str | None = None
    process_id: int | None = None
    confidence: float = 0.0
    raw_reference: dict[str, Any] | None = None
    incident_id: str | None = None

    def sort_key(self) -> tuple[str, int, str]:
        return (self.timestamp_utc or "", _KIND_ORDER.get(self.event_type.value, 99), self.event_type.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "event_type": self.event_type.value,
            "source": self.source,
            "title": self.title,
            "details": self.details,
            "process_guid": self.process_guid,
            "process_id": self.process_id,
            "confidence": self.confidence,
            "raw_reference": self.raw_reference,
            "incident_id": self.incident_id,
        }


# Backward alias
TimelineEvent = ProxyTimelineEvent

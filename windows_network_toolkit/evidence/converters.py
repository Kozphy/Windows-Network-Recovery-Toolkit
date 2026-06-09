"""Convert legacy artefact shapes into EvidenceEvent rows."""

from __future__ import annotations

import uuid
from typing import Any

from .evidence_model import EvidenceEvent


def from_collector_dict(
    payload: dict[str, Any],
    *,
    signal: str,
    category: str = "collector",
    source: str = "collector",
    timestamp: str,
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=str(payload.get("event_id") or uuid.uuid4()),
        timestamp=timestamp,
        source=str(payload.get("source") or source),
        category=category,
        signal=signal,
        observed_value=str(payload),
        raw_data=dict(payload),
    )


def from_proxy_timeline_event(event: Any) -> EvidenceEvent:
    event_type = getattr(event, "event_type", None)
    signal = event_type.value if hasattr(event_type, "value") else str(event_type or "UNKNOWN")
    return EvidenceEvent(
        event_id=str(uuid.uuid4()),
        timestamp=str(getattr(event, "timestamp_utc", "") or ""),
        source=str(getattr(event, "source", "") or "timeline"),
        category="timeline",
        signal=signal,
        observed_value=str(getattr(event, "title", "") or ""),
        process_name="",
        pid=getattr(event, "process_id", None),
        confidence=float(getattr(event, "confidence", 0.0) or 0.0),
        severity="high" if signal in {"REGISTRY_VALUE_SET", "LOCALHOST_LISTENER_OBSERVED"} else "medium",
        raw_data=dict(getattr(event, "raw_reference", None) or {}),
    )


def from_signal_dict(name: str, value: Any, *, timestamp: str, source: str = "fixture") -> EvidenceEvent:
    return EvidenceEvent(
        event_id=str(uuid.uuid4()),
        timestamp=timestamp,
        source=source,
        category="signal",
        signal=name,
        observed_value=str(value),
        raw_data={"name": name, "value": value},
    )

"""Normalized evidence record for ingestion prior to attribution correlation.

Detached from persistence — callers serialize into ``EvidenceEvent.payload`` envelopes or append JSONL shards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EvidenceSubtype = Literal["procmon_csv", "sysmon_eid13", "etw_stub", "registry_poll", "listener_hint", "other"]


@dataclass
class EvidenceEvent:
    """Single correlated evidence datum prior to fused :class:`~evidence.models.AttributionResult`."""

    event_id: str
    timestamp_utc: str
    endpoint_id: str
    schema_version: str = "1"
    evidence_type: EvidenceSubtype | str = "other"
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

"""Typed models for registry-write telemetry and fused writer evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

RegistryWriteSource = Literal["sysmon", "windows_eventlog", "etw", "fixture"]
EvidenceLevel = Literal[
    "NO_TELEMETRY",
    "NO_RELEVANT_REGISTRY_WRITES",
    "REGISTRY_WRITER_OBSERVED",
    "WRITER_AND_LISTENER_MATCH",
    "CONFLICTING_EVIDENCE",
    "INCONCLUSIVE",
]
ConfidenceRank = Literal["none", "low", "medium", "high"]

PROXY_REGISTRY_VALUE_NAMES = frozenset(
    {
        "ProxyEnable",
        "ProxyServer",
        "AutoConfigURL",
        "ProxyOverride",
    }
)


@dataclass
class RegistryWriteEvent:
    timestamp_utc: datetime
    source: RegistryWriteSource
    event_id: int | None = None
    registry_path: str = ""
    registry_value_name: str | None = None
    registry_value_data: str | None = None
    process_guid: str | None = None
    process_id: int | None = None
    process_name: str | None = None
    process_path: str | None = None
    command_line: str | None = None
    user: str | None = None
    raw_event: dict[str, Any] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp_utc"] = self.timestamp_utc.isoformat()
        if not include_raw:
            payload.pop("raw_event", None)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryWriteEvent:
        ts = data.get("timestamp_utc")
        if isinstance(ts, str):
            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        elif isinstance(ts, datetime):
            timestamp = ts
        else:
            timestamp = datetime.fromisoformat("1970-01-01T00:00:00+00:00")
        return cls(
            timestamp_utc=timestamp,
            source=data.get("source") or "fixture",
            event_id=data.get("event_id"),
            registry_path=str(data.get("registry_path") or ""),
            registry_value_name=data.get("registry_value_name"),
            registry_value_data=data.get("registry_value_data"),
            process_guid=data.get("process_guid"),
            process_id=data.get("process_id"),
            process_name=data.get("process_name"),
            process_path=data.get("process_path"),
            command_line=data.get("command_line"),
            user=data.get("user"),
            raw_event=dict(data.get("raw_event") or {}),
            parse_warnings=list(data.get("parse_warnings") or []),
        )


@dataclass
class ProxyTelemetryWindow:
    start_utc: datetime
    end_utc: datetime
    events: list[RegistryWriteEvent] = field(default_factory=list)

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        return {
            "start_utc": self.start_utc.isoformat(),
            "end_utc": self.end_utc.isoformat(),
            "events": [event.to_dict(include_raw=include_raw) for event in self.events],
        }


@dataclass
class RegistryWriterEvidence:
    evidence_level: EvidenceLevel
    matched_events: list[RegistryWriteEvent] = field(default_factory=list)
    candidate_writers: list[dict[str, Any]] = field(default_factory=list)
    listener_match: dict[str, Any] | None = None
    limitations: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)
    confidence_rank: ConfidenceRank = "none"

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        return {
            "evidence_level": self.evidence_level,
            "matched_events": [
                event.to_dict(include_raw=include_raw) for event in self.matched_events
            ],
            "candidate_writers": list(self.candidate_writers),
            "listener_match": self.listener_match,
            "limitations": list(self.limitations),
            "recommended_next_steps": list(self.recommended_next_steps),
            "confidence_rank": self.confidence_rank,
        }

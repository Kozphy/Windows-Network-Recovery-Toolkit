"""Typed evidence models for the Endpoint Reliability Decision Platform."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]


class EvidenceEvent(BaseModel):
    event_id: str
    timestamp: str
    source: str
    category: str
    signal: str
    observed_value: str = ""
    expected_value: str = ""
    process_name: str = ""
    pid: int | None = None
    command_line: str = ""
    registry_path: str = ""
    local_address: str = ""
    remote_address: str = ""
    port: int | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    severity: Severity = "medium"
    raw_data: dict[str, Any] = Field(default_factory=dict)

    def dedupe_key(self) -> tuple[str, str, str]:
        return (self.timestamp, self.signal, self.observed_value)


class EvidenceBundle(BaseModel):
    incident_id: str
    created_at: str
    host_id: str = "local"
    events: list[EvidenceEvent] = Field(default_factory=list)
    summary: str = ""
    tags: list[str] = Field(default_factory=list)

    def to_timeline_json(self) -> list[dict[str, Any]]:
        return [
            {
                "timestamp": ev.timestamp,
                "signal": ev.signal,
                "observed_value": ev.observed_value,
                "severity": ev.severity,
            }
            for ev in sorted(self.events, key=lambda e: e.timestamp)
        ]

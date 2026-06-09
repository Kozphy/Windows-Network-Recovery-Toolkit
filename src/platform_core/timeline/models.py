"""Incident timeline entry model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.evidence.record import ConfidenceOrdinal


class TimelineEntry(BaseModel):
    timestamp: str
    event_type: str
    actor: str = "platform"
    object: str = ""
    before_state: str = ""
    after_state: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceOrdinal = "medium"
    limitations: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

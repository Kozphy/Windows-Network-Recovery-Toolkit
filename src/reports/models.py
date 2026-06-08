"""Evidence tree models — Step 5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceNode:
    id: str
    parent_id: str | None
    node_type: str
    title: str
    summary: str = ""
    timestamp_utc: str | None = None
    source: str = ""
    confidence: float = 0.0
    severity: str | None = None
    raw_event_reference: dict[str, Any] | None = None
    children: list[EvidenceNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "node_type": self.node_type,
            "title": self.title,
            "summary": self.summary,
            "timestamp_utc": self.timestamp_utc,
            "source": self.source,
            "confidence": self.confidence,
            "severity": self.severity,
            "raw_event_reference": self.raw_event_reference,
            "children": [c.to_dict() for c in self.children],
            "label": self.title,
            "explanation": self.summary,
        }

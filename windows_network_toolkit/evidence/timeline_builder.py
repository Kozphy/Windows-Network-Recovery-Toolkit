"""Merge collector and fixture signals into a chronological evidence timeline."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from platform_core.models import utc_now_iso

from .converters import from_proxy_timeline_event, from_signal_dict
from .evidence_model import EvidenceBundle, EvidenceEvent


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class TimelineBuilder:
    """Build deduplicated evidence timelines from signals and legacy artefacts."""

    def __init__(self, *, incident_id: str | None = None, host_id: str = "local") -> None:
        self.incident_id = incident_id or f"incident-{uuid.uuid4().hex[:12]}"
        self.host_id = host_id
        self._events: list[EvidenceEvent] = []

    def add_signal(self, name: str, value: Any, *, timestamp: str | None = None, source: str = "signal") -> None:
        self._events.append(
            from_signal_dict(name, value, timestamp=timestamp or _now_iso(), source=source)
        )

    def add_event(self, event: EvidenceEvent) -> None:
        self._events.append(event)

    def ingest_collector_payload(self, payload: dict[str, Any], *, prefix: str = "") -> None:
        ts = str(payload.get("timestamp") or _now_iso())
        for key, value in payload.items():
            if key in {"timestamp", "source"}:
                continue
            signal = f"{prefix}{key}".upper() if prefix else key.upper()
            self.add_signal(signal, value, timestamp=ts, source=str(payload.get("source") or "collector"))

    def ingest_jsonl(self, path: Path | str) -> None:
        p = Path(path)
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            ts = str(row.get("timestamp") or row.get("timestamp_utc") or _now_iso())
            if "signal" in row:
                self.add_signal(str(row["signal"]), row.get("observed_value", row.get("value")), timestamp=ts)
            elif "name" in row:
                self.add_signal(str(row["name"]), row.get("value"), timestamp=ts)
            else:
                self.ingest_collector_payload(row)

    def merge_proxy_timeline(self, events: list[Any]) -> None:
        for ev in events:
            self._events.append(from_proxy_timeline_event(ev))

    def build(self, *, summary: str = "", tags: list[str] | None = None) -> EvidenceBundle:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[EvidenceEvent] = []
        for ev in sorted(self._events, key=lambda e: e.timestamp):
            key = ev.dedupe_key()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ev)
        return EvidenceBundle(
            incident_id=self.incident_id,
            created_at=utc_now_iso(),
            host_id=self.host_id,
            events=deduped,
            summary=summary,
            tags=tags or [],
        )

    def to_timeline_json(self, bundle: EvidenceBundle | None = None) -> list[dict[str, Any]]:
        b = bundle or self.build()
        return b.to_timeline_json()

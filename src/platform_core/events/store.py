"""Append-only trisk domain event store."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from platform_core import storage
from src.platform_core.events.models import TriskDomainEvent, TriskEventType

CANONICAL_LOG = "trisk_domain_events.jsonl"


def _log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    base = Path(os.getenv("PLATFORM_DATA_DIR", "platform_data"))
    return base / CANONICAL_LOG


class TriskEventStore:
    """JSONL event store with per-aggregate sequence."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = _log_path(path)
        self._sequence_cache: dict[str, int] | None = None

    def _load_sequences(self) -> dict[str, int]:
        if self._sequence_cache is not None:
            return self._sequence_cache
        seq: dict[str, int] = {}
        for row in storage.iter_jsonl(self._path):
            if not isinstance(row, dict):
                continue
            agg = str(row.get("aggregate_id") or "")
            seq_num = int(row.get("sequence") or 0)
            if agg:
                seq[agg] = max(seq.get(agg, 0), seq_num)
        self._sequence_cache = seq
        return seq

    def next_sequence(self, aggregate_id: str) -> int:
        return self._load_sequences().get(aggregate_id, 0) + 1

    def append(self, event: TriskDomainEvent) -> TriskDomainEvent:
        storage.append_jsonl(self._path, event.model_dump(mode="json"))
        if self._sequence_cache is not None:
            self._sequence_cache[event.aggregate_id] = event.sequence
        self._mirror_db(event)
        return event

    def _mirror_db(self, event: TriskDomainEvent) -> None:
        try:
            from sqlmodel import Session

            from backend.db import get_engine, init_trisk_schema
            from backend.db.models import TriskDomainEventRow

            init_trisk_schema()
            with Session(get_engine()) as session:
                session.add(
                    TriskDomainEventRow(
                        event_id=event.event_id,
                        event_type=event.event_type.value,
                        aggregate_id=event.aggregate_id,
                        aggregate_type=event.aggregate_type,
                        sequence=event.sequence,
                        actor=event.actor,
                        correlation_id=event.correlation_id,
                        payload=dict(event.payload),
                        limitations=list(event.limitations),
                    )
                )
                session.commit()
        except Exception:
            pass

    def iter_events(
        self,
        *,
        aggregate_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Iterator[TriskDomainEvent]:
        rows: list[dict[str, Any]] = []
        for row in storage.iter_jsonl(self._path):
            if not isinstance(row, dict):
                continue
            if aggregate_id and row.get("aggregate_id") != aggregate_id:
                continue
            rows.append(row)
        for row in rows[offset : offset + limit]:
            yield TriskDomainEvent.model_validate(row)

    def list_events(
        self,
        *,
        aggregate_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TriskDomainEvent]:
        return list(self.iter_events(aggregate_id=aggregate_id, limit=limit, offset=offset))


_default_store: TriskEventStore | None = None


def get_event_store() -> TriskEventStore:
    global _default_store
    if _default_store is None:
        _default_store = TriskEventStore()
    return _default_store


def reset_event_store() -> None:
    global _default_store
    _default_store = None


def emit_trisk_event(
    event_type: TriskEventType,
    *,
    aggregate_id: str,
    aggregate_type: str = "evidence",
    actor: str = "system",
    correlation_id: str = "",
    payload: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> TriskDomainEvent:
    store = get_event_store()
    event = TriskDomainEvent(
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,  # type: ignore[arg-type]
        sequence=store.next_sequence(aggregate_id),
        actor=actor,
        correlation_id=correlation_id or aggregate_id,
        payload=payload or {},
        limitations=limitations or [],
    )
    store.append(event)
    try:
        from backend.trisk_metrics import inc

        inc("domain_events_appended_total", labels={"event_type": event_type.value})
    except Exception:
        pass
    return event

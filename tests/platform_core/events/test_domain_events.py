"""Domain event store tests."""

from __future__ import annotations

import pytest

from src.platform_core.events import (
    TriskEventType,
    emit_trisk_event,
    get_event_store,
    reset_event_store,
)
from src.platform_core.events.replay import replay_events


@pytest.fixture(autouse=True)
def _clean_events(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path))
    reset_event_store()
    yield
    reset_event_store()


def test_emit_and_list_events():
    emit_trisk_event(
        TriskEventType.EVIDENCE_COLLECTED,
        aggregate_id="evidence:evt-1",
        aggregate_type="evidence",
        payload={"event_id": "evt-1"},
    )
    events = get_event_store().list_events()
    assert len(events) == 1
    assert events[0].event_type == TriskEventType.EVIDENCE_COLLECTED


def test_sequence_increments():
    agg = "incident:INC-1"
    emit_trisk_event(TriskEventType.INCIDENT_DETECTED, aggregate_id=agg, aggregate_type="incident")
    emit_trisk_event(TriskEventType.RISK_CLASSIFIED, aggregate_id=agg, aggregate_type="incident")
    events = list(get_event_store().iter_events(aggregate_id=agg, limit=10))
    assert [e.sequence for e in events] == [1, 2]


def test_replay_fixture(tmp_path):
    fixture = tmp_path / "events.jsonl"
    fixture.write_text(
        '{"event_id":"devt-test-1","event_type":"EvidenceCollected","aggregate_id":"evidence:e1","aggregate_type":"evidence","sequence":1,"actor":"test","payload":{},"limitations":[]}\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    emitted = replay_events(fixture, out_path=out)
    assert len(emitted) == 1
    assert out.is_file()

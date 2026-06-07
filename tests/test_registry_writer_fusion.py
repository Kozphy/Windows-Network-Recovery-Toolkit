"""Tests for registry writer telemetry fusion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from telemetry.registry_writer_fusion import (
    default_no_telemetry_evidence,
    fuse_registry_writer_evidence,
)
from telemetry.sysmon_reader import parse_sysmon_registry_event

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "telemetry"
PROXY_CHANGE_TIME = datetime(2026, 1, 15, 12, 0, 10, tzinfo=timezone.utc)


def _load_events(name: str) -> list:
    raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else [raw]
    events = []
    for row in rows:
        parsed = parse_sysmon_registry_event(row)
        if parsed is not None:
            events.append(parsed)
    return events


def test_no_telemetry_returns_no_telemetry_level() -> None:
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=[],
    )
    assert evidence.evidence_level == "NO_TELEMETRY"
    assert evidence.confidence_rank == "none"


def test_default_no_telemetry_helper() -> None:
    evidence = default_no_telemetry_evidence()
    assert evidence.evidence_level == "NO_TELEMETRY"
    assert any("No Sysmon/EventLog/ETW" in item for item in evidence.limitations)


def test_writer_and_listener_match() -> None:
    events = _load_events("sysmon_event13_proxy_enable_node.json")
    events.extend(_load_events("sysmon_event13_proxy_server_node.json"))
    listener = json.loads((FIXTURES / "listener_node.json").read_text(encoding="utf-8"))
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
        listener_attribution=listener,
    )
    assert evidence.evidence_level == "WRITER_AND_LISTENER_MATCH"
    assert evidence.confidence_rank == "high"
    assert evidence.listener_match is not None
    assert evidence.listener_match["matched"] is True


def test_conflicting_writer_and_listener() -> None:
    events = _load_events("conflicting_writer.json")
    listener = json.loads((FIXTURES / "listener_conflicting.json").read_text(encoding="utf-8"))
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
        listener_attribution=listener,
    )
    assert evidence.evidence_level == "CONFLICTING_EVIDENCE"
    assert evidence.listener_match is not None
    assert evidence.listener_match["matched"] is False
    assert any("unresolved" in item.lower() for item in evidence.limitations)


def test_missing_fields_inconclusive() -> None:
    events = _load_events("missing_fields.json")
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
    )
    assert evidence.evidence_level == "INCONCLUSIVE"
    assert evidence.confidence_rank == "low"


def test_non_proxy_event_in_window_is_no_relevant_writes() -> None:
    raw = {
        "EventID": 13,
        "UtcTime": "2026-01-15T12:00:05.000Z",
        "TargetObject": r"HKCU\Software\Demo\App\Setting",
        "Image": r"C:\Windows\System32\cmd.exe",
        "ProcessId": 1,
    }
    event = parse_sysmon_registry_event(raw)
    assert event is not None
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=[event],
    )
    assert evidence.evidence_level == "NO_RELEVANT_REGISTRY_WRITES"


def test_registry_writer_observed_without_listener() -> None:
    events = _load_events("sysmon_event13_proxy_server_node.json")
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
        listener_attribution=None,
    )
    assert evidence.evidence_level == "REGISTRY_WRITER_OBSERVED"
    assert evidence.confidence_rank == "medium"

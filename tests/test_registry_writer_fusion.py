"""Tests for registry writer telemetry fusion (Tier-1 evidence ladder)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from telemetry.registry_writer_fusion import (
    default_no_telemetry_evidence,
    fuse_registry_writer_evidence,
)
from telemetry.sysmon_parser import parse_sysmon_registry_event

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "telemetry"
PROXY_CHANGE_TIME = datetime(2026, 1, 15, 12, 0, 10, tzinfo=UTC)


def _load_events(name: str) -> list:
    raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else [raw]
    events = []
    for row in rows:
        parsed = parse_sysmon_registry_event(row)
        if parsed is not None:
            events.append(parsed)
    return events


def test_no_telemetry_no_listener_is_no_writer_evidence() -> None:
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=[],
    )
    assert evidence.evidence_level == "NO_WRITER_EVIDENCE"


def test_listener_alone_is_listener_observed_not_writer_proof() -> None:
    listener = json.loads((FIXTURES / "listener_node.json").read_text(encoding="utf-8"))
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=[],
        listener_attribution=listener,
    )
    assert evidence.evidence_level == "LISTENER_OBSERVED"
    assert any("does not prove" in item.lower() for item in evidence.limitations)


def test_sysmon_writer_alone_is_registry_writer_observed() -> None:
    events = _load_events("sysmon_event13_proxy_server_node.json")
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
    )
    assert evidence.evidence_level == "REGISTRY_WRITER_OBSERVED"
    assert evidence.confidence_rank == "medium"


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
    assert evidence.listener_match is not None
    assert evidence.listener_match["matched"] is True


def test_writer_listener_mismatch() -> None:
    events = _load_events("conflicting_writer.json")
    listener = json.loads((FIXTURES / "listener_conflicting.json").read_text(encoding="utf-8"))
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
        listener_attribution=listener,
    )
    assert evidence.evidence_level == "WRITER_LISTENER_MISMATCH"


def test_missing_fields_inconclusive() -> None:
    events = _load_events("missing_fields.json")
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=PROXY_CHANGE_TIME,
        telemetry_events=events,
    )
    assert evidence.evidence_level == "INCONCLUSIVE"


def test_malformed_fixture_fails_safely() -> None:
    assert parse_sysmon_registry_event({"EventID": 1}) is None
    assert parse_sysmon_registry_event({}) is None


def test_default_no_telemetry_helper() -> None:
    evidence = default_no_telemetry_evidence()
    assert evidence.evidence_level == "NO_WRITER_EVIDENCE"

"""Step 4 — timeline replay tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.proxy_guard.incident_pipeline import analyze_fixture
from src.replay.fixture_loader import load_all_fixtures, load_fixture
from src.replay.models import ProxyTimelineEventType
from src.replay.proxy_timeline import build_timeline_from_fixture, render_timeline_json

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "proxy_incidents"


def test_events_sorted_by_timestamp_and_kind() -> None:
    events = build_timeline_from_fixture(load_fixture(FIXTURES / "unknown_node_powershell_proxy.json"))
    keys = [e.sort_key() for e in events]
    assert keys == sorted(keys)


def test_correlation_only_fixture_has_state_change() -> None:
    events = build_timeline_from_fixture(load_fixture(FIXTURES / "correlation_only_listener.json"))
    types = {e.event_type for e in events}
    assert ProxyTimelineEventType.PROXY_STATE_CHANGED in types
    assert ProxyTimelineEventType.POLICY_DECISION_CREATED in types


def test_multiple_fixtures_separate_incidents() -> None:
    all_fx = load_all_fixtures(FIXTURES)
    ids = {fx["incident_id"] for fx in all_fx}
    assert len(ids) >= 5


def test_policy_attached_to_correct_incident() -> None:
    bundle = analyze_fixture(load_fixture(FIXTURES / "suspicious_powershell_temp_proxy.json"))
    events = build_timeline_from_fixture(load_fixture(FIXTURES / "suspicious_powershell_temp_proxy.json"))
    policy_events = [e for e in events if e.event_type == ProxyTimelineEventType.POLICY_DECISION_CREATED]
    assert policy_events
    assert policy_events[0].raw_reference.get("decision") == bundle["policy"]["decision"]


def test_fixture_timeline_json_roundtrip() -> None:
    events = build_timeline_from_fixture(load_fixture(FIXTURES / "cursor_known_proxy.json"))
    payload = json.loads(render_timeline_json(events))
    assert len(payload["events"]) >= 3

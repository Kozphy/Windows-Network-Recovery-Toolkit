"""Fixture-driven proxy transition regression tests (FAANG + Big 4 audit grade)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from windows_network_toolkit.proxy_replay import replay_proxy_events
from windows_network_toolkit.proxy_state_machine import (
    FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY,
    TransitionClass,
    build_proxy_evidence_event,
    classify_transition,
    validate_classification_safety,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "proxy_transitions"


def _load_json_fixtures() -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append((path.name, data))
    return rows


@pytest.mark.parametrize("fixture_name,fixture", _load_json_fixtures())
def test_proxy_transition_fixture(fixture_name: str, fixture: dict) -> None:
    before = fixture["before"]
    after = fixture["after"]
    listener = fixture.get("listener")
    health = fixture.get("health")
    event = build_proxy_evidence_event(
        before_raw=before,
        after_raw=after,
        timestamp_utc="2026-06-12T12:00:00Z",
        listener=listener,
        health=health,
    )
    classification = event["classification"]
    assert classification["confidence_semantics"] == "ordinal_not_probability"
    assert classification["limitations"]
    assert classification["unsafe_inferences_blocked"]

    expected_primary = fixture.get("expected_primary")
    if expected_primary:
        assert classification["primary_classification"] == expected_primary

    expected_transition = fixture.get("expected_transition")
    if expected_transition:
        assert event["transition_class"] == expected_transition

    expected_any = fixture.get("expected_transition_any_of")
    if expected_any:
        assert event["transition_class"] in expected_any

    for forbidden in fixture.get("must_not_classify_as") or []:
        assert forbidden not in event["transition_class"]
        assert forbidden not in classification["primary_classification"]
        assert forbidden not in json.dumps(event)

    for signal in fixture.get("expected_secondary_contains") or []:
        assert signal in classification["secondary_signals"]

    assert classification["safety_violations"] == []


def test_after_proxy_server_none_is_never_remote_proxy_configured() -> None:
    cases = [
        (
            {"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"},
            {"wininet_proxy_enabled": True, "wininet_proxy_server": None},
        ),
        (
            {"wininet_proxy_enabled": True, "wininet_proxy_server": "10.0.0.5:8080"},
            {"wininet_proxy_enabled": True, "wininet_proxy_server": None},
        ),
        (
            {"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"},
            {"wininet_proxy_enabled": False, "wininet_proxy_server": None},
        ),
    ]
    for before, after in cases:
        event = build_proxy_evidence_event(
            before_raw=before,
            after_raw=after,
            timestamp_utc="2026-06-12T12:00:01Z",
        )
        blob = json.dumps(event)
        for forbidden in FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY:
            assert forbidden not in event["transition_class"]
            assert forbidden not in event["classification"]["primary_classification"]
            assert forbidden not in blob
        assert event["classification"]["safety_violations"] == []


def test_validate_classification_safety_catches_violation() -> None:
    violations = validate_classification_safety(
        after_proxy_server=None,
        primary_classification="REMOTE_PROXY_CONFIGURED",
        transition_class="REMOTE_OR_NON_LOOPBACK_PROXY_CONFIGURED",
    )
    assert violations


def test_proxy_enable_0_to_1_localhost() -> None:
    before = {"wininet_proxy_enabled": False, "wininet_proxy_server": ""}
    after = {"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"}
    event = build_proxy_evidence_event(before_raw=before, after_raw=after, timestamp_utc="2026-06-12T12:00:00Z")
    assert event["transition_class"] == TransitionClass.LOCALHOST_PROXY_ENABLED.value
    assert event["classification"]["primary_classification"] == "LOCALHOST_PROXY_CONFIGURED"


def test_proxy_enable_1_to_0_server_removed() -> None:
    before = {"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"}
    after = {"wininet_proxy_enabled": False, "wininet_proxy_server": None}
    event = build_proxy_evidence_event(before_raw=before, after_raw=after, timestamp_utc="2026-06-12T12:00:01Z")
    assert event["transition_class"] == TransitionClass.PROXY_DISABLED_AND_SERVER_REMOVED.value
    assert "REMOTE" not in event["transition_class"]


def test_classification_uses_full_state_not_proxy_enable_alone() -> None:
    """ProxyEnable-only diff would miss server removal; full state yields disable+removed."""
    before = {"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"}
    after_enable_only_view = {"wininet_proxy_enabled": False, "wininet_proxy_server": "127.0.0.1:62285"}
    after_full = {"wininet_proxy_enabled": False, "wininet_proxy_server": None}
    tc_enable_only = classify_transition(before, after_enable_only_view)
    tc_full = classify_transition(before, after_full)
    assert tc_enable_only == TransitionClass.PROXY_DISABLED
    assert tc_full == TransitionClass.PROXY_DISABLED_AND_SERVER_REMOVED
    assert tc_enable_only != tc_full


def test_listener_present_proxy_probe_fails() -> None:
    fixture = json.loads((FIXTURE_DIR / "listener_probe_failed.json").read_text(encoding="utf-8"))
    event = build_proxy_evidence_event(
        before_raw=fixture["before"],
        after_raw=fixture["after"],
        listener=fixture.get("listener"),
        health=fixture.get("health"),
        timestamp_utc="2026-06-12T12:00:02Z",
    )
    assert "DIRECT_OK_PROXY_FAIL" in event["classification"]["secondary_signals"]
    assert "LISTENER_PRESENT" in event["classification"]["secondary_signals"]


def test_proxy_flapping_loop_replay() -> None:
    path = FIXTURE_DIR / "proxy_enable_flapping_loop.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = replay_proxy_events(rows, coalesce_ms=1000)
    assert payload["summary"]["reverter_loop_detected"] is True
    last = payload["events"][-1]
    assert last.get("transition_class") in {
        "REVERTER_SUSPECTED_LOCALHOST_PROXY_LOOP",
        "LOCALHOST_PROXY_ENABLED",
        "PROXY_DISABLED",
        "PROXY_DISABLED_AND_SERVER_REMOVED",
    }

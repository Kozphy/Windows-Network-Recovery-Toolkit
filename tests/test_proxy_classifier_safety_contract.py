"""CI safety contract tests for proxy classifier and governance language."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from windows_network_toolkit.proxy_state_machine import (
    FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY,
    build_explainable_classification,
    build_proxy_evidence_event,
    classify_transition,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "proxy_transitions" / "localhost_proxy_removed.json"


def test_listener_not_treated_as_registry_writer_proof() -> None:
    event = build_proxy_evidence_event(
        before_raw={"wininet_proxy_enabled": False, "wininet_proxy_server": ""},
        after_raw={"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"},
        listener={"process": {"name": "node.exe", "pid": 1}},
        writer_proof=False,
    )
    blocked = event["classification"]["unsafe_inferences_blocked"]
    assert any("registry writer" in b.lower() for b in blocked)
    assert event["attribution"]["kind"] == "correlation"
    assert event["proof_tier"] in ("T1", "T2")


def test_listener_not_proof_of_safe_proxy() -> None:
    event = build_proxy_evidence_event(
        before_raw={"wininet_proxy_enabled": False, "wininet_proxy_server": ""},
        after_raw={"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"},
        listener={"process": {"name": "node.exe", "pid": 1}},
        health={"tcp_listening": True, "proxy_probe_ok": False, "direct_probe_ok": True},
    )
    assert "DIRECT_OK_PROXY_FAIL" in event["classification"]["secondary_signals"]
    blob = json.dumps(event).lower()
    assert "malware confirmed" not in blob
    assert "compromise proven" not in blob


def test_no_malware_verdict_in_classification_output() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    event = build_proxy_evidence_event(
        before_raw=fixture["before"],
        after_raw=fixture["after"],
        timestamp_utc="2026-06-12T12:00:00Z",
    )
    blob = json.dumps(event).lower()
    for phrase in ("malware confirmed", "attacker detected", "compromise proven"):
        assert phrase not in blob


@pytest.mark.parametrize(
    "after_server",
    [None, "", "   "],
)
def test_empty_after_server_never_remote_primary(after_server: str | None) -> None:
    before = {"wininet_proxy_enabled": True, "wininet_proxy_server": "127.0.0.1:62285"}
    after = {"wininet_proxy_enabled": True, "wininet_proxy_server": after_server}
    transition = classify_transition(before, after)
    explain = build_explainable_classification(
        before_raw=before,
        after_raw=after,
        transition=transition,
    )
    assert explain["primary_classification"] not in FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY
    assert explain["safety_violations"] == []

"""Tests for incident lifecycle engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.incident_engine import (
    apply_transition,
    can_transition,
    evaluate_incident_candidate,
)
from platform_core.incident_store import get_incident


def test_incident_state_transitions_valid() -> None:
    assert can_transition("OPEN", "ACKNOWLEDGED")
    assert can_transition("ACKNOWLEDGED", "RESOLVED")
    assert not can_transition("RESOLVED", "OPEN")


def test_invalid_transition_rejected(tmp_path: Path, monkeypatch) -> None:
    store = tmp_path / "incidents.jsonl"
    monkeypatch.setattr("platform_core.incident_store._path", lambda name: store)

    record = evaluate_incident_candidate(
        endpoint_id="demo-endpoint-001",
        observations=[
            {"name": "browser_https_failed"},
            {"name": "wininet_proxy_enabled"},
            {"name": "proxy_bypass_succeeded"},
        ],
    )
    assert record is not None
    apply_transition(record.incident_id, new_state="RESOLVED")
    with pytest.raises(ValueError, match="invalid transition"):
        apply_transition(record.incident_id, new_state="OPEN")


def test_weak_evidence_cannot_create_critical_incident(tmp_path: Path, monkeypatch) -> None:
    store = tmp_path / "incidents.jsonl"
    monkeypatch.setattr("platform_core.incident_store._path", lambda name: store)

    record = evaluate_incident_candidate(
        endpoint_id="demo-endpoint-001",
        observations=[
            {"name": "browser_https_failed"},
            {"name": "wininet_proxy_enabled"},
            {"name": "proxy_bypass_succeeded"},
        ],
        evidence_level="observation",
    )
    assert record is not None
    assert record.severity != "critical"
    row = get_incident(record.incident_id, store_path=store)
    assert row is not None

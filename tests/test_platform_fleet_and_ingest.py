"""Offline tests for fleet seeding, ingest route aliases, policy verbs, and attribution coercion.

Module responsibility:
    Guard portfolio additions ``demo_fleet``, ``/platform/ingest/*``, and ``policy_engine`` without live HTTP servers
    beyond FastAPI ``TestClient`` fixtures.

System placement:
    Complements ``tests/test_api_platform_routes.py`` with narrower ingest-alias coverage.

Side effects:
    Uses ``tmp_path`` / monkeypatch only—no writes to developer ``platform_data/``.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from evidence.models import coerce_attribution_level
from platform_core.demo_fleet import populate_fleet
from platform_core.metrics import compute_platform_metrics
from platform_core.platform_event_contract import EndpointHeartbeat, PlatformEventEnvelope
from platform_core.policy_engine import evaluate_route_decision


def test_coerce_legacy_attribution_level() -> None:
    assert coerce_attribution_level("confirmed_by_eventlog") == "sysmon_confirmed"
    assert coerce_attribution_level("evidence_supported") == "procmon_confirmed"


def test_platform_event_contract_model() -> None:
    hb = EndpointHeartbeat(event_id="e1", endpoint_id="0" * 32, timestamp_utc="2026-01-01T00:00:00+00:00")
    assert hb.event_type == "endpoint.heartbeat"
    envelope = PlatformEventEnvelope(event_id="x", endpoint_id="0" * 32, event_type="custom", payload={"a": 1})
    assert envelope.payload["a"] == 1


@pytest.fixture()
def ingest_client(monkeypatch, tmp_path):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", lambda: tmp_path)

    from backend.main import app

    return TestClient(
        app,
        headers={
            "X-Operator-Role": "operator",
            "X-Operator-Id": "pytest-ingest",
        },
    )


def test_ingest_aliases_match_legacy_paths(ingest_client: TestClient) -> None:
    hb = {"endpoint_id": "ingest-ep-1", "os_family": "Windows", "os_version": "11", "agent_version": "t"}
    r = ingest_client.post("/platform/ingest/heartbeat", json=hb)
    assert r.status_code == 200
    legacy = ingest_client.post("/platform/agent/heartbeat", json=hb | {"endpoint_id": "ingest-ep-2"})
    assert legacy.status_code == 200

    snap = {
        "endpoint_id": "ingest-ep-1",
        "network_state": {},
        "proxy_state": {},
        "dns_state": {},
        "tcp_state": {},
        "browser_path_state": {},
        "process_clues": {},
        "raw_data_redacted": True,
    }
    r2 = ingest_client.post("/platform/ingest/snapshot", json=snap)
    assert r2.status_code == 200


def test_policy_engine_blocking_high_risk() -> None:
    verb, detail = evaluate_route_decision(
        remediation_action="reset_firewall",
        operator_role="admin",
        signal_bundle={"summary": "", "proxy_server": "127.0.0.1:8899"},
    )
    assert verb == "block"
    assert detail["structured"]["execute_allowed"] is False


def test_demo_fleet_populates_metrics(monkeypatch, tmp_path) -> None:
    populate_fleet(tmp_path, reset=True)
    metrics = compute_platform_metrics(platform_root=tmp_path)
    assert metrics.get("endpoint_count", 0) >= 1
    assert "open_failure_events" in metrics

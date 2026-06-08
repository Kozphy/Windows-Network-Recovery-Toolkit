"""Step 5 — proxy incident API tests (fixture mode, isolated app)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes_evidence_tree import router as evidence_router
from src.api.routes_proxy_incidents import router as incidents_router


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PLATFORM_FIXTURE_MODE", "1")
    monkeypatch.setenv("PLATFORM_REPO_ROOT", str(Path(__file__).resolve().parents[1]))
    app = FastAPI()
    app.include_router(incidents_router)
    app.include_router(evidence_router)
    return TestClient(app)


def test_list_incidents(client: TestClient) -> None:
    r = client.get("/api/proxy/incidents")
    assert r.status_code == 200
    assert len(r.json()["incidents"]) >= 5


def test_get_incident_by_fixture_id(client: TestClient) -> None:
    r = client.get("/api/proxy/incidents/cursor_known_proxy")
    assert r.status_code == 200
    assert r.json()["incident_id"] == "cursor_known_proxy"


def test_evidence_tree_nodes(client: TestClient) -> None:
    r = client.get("/api/proxy/incidents/unknown_node_powershell_proxy/evidence-tree")
    assert r.status_code == 200
    tree = r.json()["evidence_tree"]
    assert tree["title"] == "Observation"


def test_correlation_only_marked(client: TestClient) -> None:
    r = client.get("/api/proxy/incidents/correlation_only_listener")
    assert r.status_code == 200
    assert r.json()["status"] == "correlation_only"
    pol = client.get("/api/proxy/incidents/correlation_only_listener/policy").json()
    assert pol["policy"]["decision"] == "CORRELATION_ONLY_ALERT"


def test_timeline_endpoint(client: TestClient) -> None:
    r = client.get("/api/proxy/incidents/cursor_known_proxy/timeline")
    assert r.status_code == 200
    assert len(r.json()["events"]) >= 1

"""Dashboard fixture API route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

FLEET = "tests/fixtures/fleet/fleet_100_endpoints.jsonl"
HEADERS = {"X-Operator-Role": "viewer", "X-Operator-Id": "pytest-dashboard"}


def test_fleet_summary_fixture_route() -> None:
    with TestClient(app) as client:
        resp = client.get(f"/platform/fleet/summary?fixture={FLEET}", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_endpoints"] == 100
    assert body["audit_chain"]["ok"] is True
    assert body["remediation_preview_status"]["dry_run_default"] is True


def test_fleet_replay_fixture_route() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/platform/fleet/replay",
            headers=HEADERS,
            json={"fixture_path": FLEET, "dry_run": True},
        )
    assert resp.status_code == 200
    assert resp.json()["content_digest"]
    assert resp.json()["dry_run"] is True


def test_fleet_replay_blocks_live_mutation() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/platform/fleet/replay",
            headers=HEADERS,
            json={"fixture_path": FLEET, "dry_run": False},
        )
    assert resp.status_code == 403


def test_demo_case_studies_route() -> None:
    with TestClient(app) as client:
        resp = client.get("/platform/demo/case-studies", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    ids = {item["case_id"] for item in body["items"]}
    assert "case_1_dead_wininet_proxy" in ids

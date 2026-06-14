"""FastAPI agent route tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src.platform_core.agent.usage_limits import get_usage_limiter


@pytest.fixture
def agent_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path))
    get_usage_limiter().reset()
    with TestClient(app) as client:
        yield client, tmp_path


FIXTURE = str(Path("case_studies/cs1_wininet_proxy_drift/fixture.json"))


def test_agent_ask_fixture_safe(agent_client) -> None:
    client, _tmp = agent_client
    resp = client.post(
        "/agent/ask",
        headers={"X-Operator-Role": "viewer", "X-Operator-Id": "pytest"},
        json={
            "user_id": "pytest",
            "team_id": "t1",
            "role": "viewer",
            "message": "browser cannot connect proxy broken",
            "fixture": FIXTURE,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "DIAGNOSE_PROXY"
    assert body["dry_run"] is True
    assert body["limitations"]


def test_agent_plan_returns_steps(agent_client) -> None:
    client, _tmp = agent_client
    resp = client.post(
        "/agent/plan",
        headers={"X-Operator-Role": "operator"},
        json={"message": "disable proxy fix it", "role": "operator"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "PREVIEW_REMEDIATION"
    assert body["steps"]


def test_execute_preview_never_mutates(agent_client) -> None:
    client, tmp = agent_client
    resp = client.post(
        "/agent/execute-preview",
        headers={"X-Operator-Role": "operator"},
        json={
            "role": "operator",
            "intent": "PREVIEW_REMEDIATION",
            "fixture": FIXTURE,
            "dry_run": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["no_changes_made"] is True
    assert body["preview"]["dry_run"] is True
    audit_file = tmp / "agent-actions.jsonl"
    assert audit_file.is_file()


def test_agent_audit_admin_only(agent_client) -> None:
    client, _tmp = agent_client
    denied = client.get("/agent/audit", headers={"X-Operator-Role": "viewer"})
    assert denied.status_code == 403
    ok = client.get(
        "/agent/audit",
        headers={
            "X-Operator-Role": "admin",
            "Authorization": "Bearer dev-platform-key-change-me",
        },
    )
    assert ok.status_code == 200

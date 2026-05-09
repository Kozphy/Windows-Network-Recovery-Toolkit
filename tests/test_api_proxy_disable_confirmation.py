from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_BYPASS_USER_ID", "pytest-user")
    monkeypatch.setenv("AUTH_BYPASS_EMAIL", "pytest@example.com")
    from backend.main import app

    return TestClient(app)


def test_api_proxy_disable_defaults_to_dry_run(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_invoke(argv: list[str], *, allowed_returncodes: set[int]) -> dict[str, Any]:
        calls.append(argv)
        assert allowed_returncodes == {0, 1}
        return {
            "action_id": "disable_wininet_proxy",
            "decision": "PREVIEW",
            "dry_run": True,
            "mutated": False,
            "reason": "dry_run_preview_only",
            "audit_event_id": "audit-preview",
            "before": {},
            "after": None,
        }

    monkeypatch.setattr("backend.live_observability._invoke_src_json_status", fake_invoke)
    response = api_client.post("/api/proxy/disable", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "PREVIEW"
    assert body["dry_run"] is True
    assert body["mutated"] is False
    assert calls[0] == ["proxy-disable", "--json", "--dry-run", "true"]


def test_api_proxy_disable_live_missing_confirmation_blocks(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_invoke(argv: list[str], *, allowed_returncodes: set[int]) -> dict[str, Any]:
        assert "--confirm" not in argv
        return {
            "action_id": "disable_wininet_proxy",
            "decision": "BLOCK",
            "dry_run": False,
            "mutated": False,
            "reason": "missing_confirmation",
            "audit_event_id": "audit-block",
            "before": {},
            "after": None,
        }

    monkeypatch.setattr("backend.live_observability._invoke_src_json_status", fake_invoke)
    response = api_client.post("/api/proxy/disable", json={"dry_run": False})
    assert response.status_code == 200
    assert response.json()["decision"] == "BLOCK"
    assert response.json()["reason"] == "missing_confirmation"


def test_api_proxy_disable_live_passes_confirmation(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_invoke(argv: list[str], *, allowed_returncodes: set[int]) -> dict[str, Any]:
        calls.append(argv)
        return {
            "action_id": "disable_wininet_proxy",
            "decision": "ALLOW",
            "dry_run": False,
            "mutated": True,
            "reason": "mutation_applied_validation_ok",
            "audit_event_id": "audit-success",
            "before": {"proxy_enable": 1},
            "after": {"proxy_enable": 0},
        }

    monkeypatch.setattr("backend.live_observability._invoke_src_json_status", fake_invoke)
    response = api_client.post(
        "/api/proxy/disable",
        json={"dry_run": False, "confirmation": "DISABLE_WININET_PROXY"},
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "ALLOW"
    assert "--confirm" in calls[0]
    assert "DISABLE_WININET_PROXY" in calls[0]


def test_api_proxy_disable_preview_is_read_only_and_audited(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_preview(argv: list[str]) -> dict[str, Any]:
        assert argv == ["proxy-disable", "--json", "--dry-run", "true"]
        return {
            "action_id": "disable_wininet_proxy",
            "decision": "PREVIEW",
            "dry_run": True,
            "mutated": False,
            "reason": "dry_run_preview_only",
            "audit_event_id": "audit-preview",
            "before": {},
            "after": None,
        }

    monkeypatch.setattr("backend.live_observability._invoke_src_json", fake_preview)
    response = api_client.post("/api/proxy/disable-preview", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "PREVIEW"
    assert body["audit_event_id"] == "audit-preview"
    assert "preview_text" in body

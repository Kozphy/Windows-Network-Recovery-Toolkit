"""API remediation safety regression tests (offline, no live Windows probes)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def plat_client(monkeypatch, tmp_path):
    def target():
        return tmp_path

    monkeypatch.setattr("platform_core.storage.platform_data_dir", target)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", target)

    from backend.main import app

    return TestClient(
        app,
        headers={
            "X-Operator-Role": "admin",
            "X-Operator-Id": "pytest-safety-api",
        },
    )


def _ingest(plat_client: TestClient, event_id: str, action: str, *, category: str = "dns") -> None:
    response = plat_client.post(
        "/platform/failure-events/ingest",
        json={
            "event_id": event_id,
            "endpoint_id": "safety-ep",
            "severity": "medium",
            "category": category,
            "confidence": 0.99,
            "summary": "safety fixture",
            "recommended_action_key": action,
        },
    )
    assert response.status_code == 200, response.text


def test_execute_defaults_to_dry_run_without_subprocess(
    plat_client: TestClient, monkeypatch
) -> None:
    _ingest(plat_client, "dry-default-1", "reset_dns")
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "dry-default-1",
            "requested_action": "reset_dns",
        },
    )
    preview_id = prv.json()["preview_id"]

    def boom(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not run when dry_run defaults apply")

    monkeypatch.setattr("backend.platform_routes.subprocess.run", boom)

    ex = plat_client.post(
        "/platform/remediation/execute",
        json={
            "preview_id": preview_id,
            "confirmation_phrase": "RUN_DNS_RESET",
            # dry_run omitted — model default True
        },
    )
    assert ex.status_code == 200
    body = ex.json()
    assert body.get("result") == "dry_run"
    assert body.get("dry_run") is True


def test_arbitrary_command_action_blocked_at_preview(plat_client: TestClient) -> None:
    _ingest(plat_client, "arb-1", "arbitrary_command_forbidden", category="unknown")
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "arb-1",
            "requested_action": "arbitrary_command_forbidden",
        },
    )
    assert prv.status_code == 200
    body = prv.json()
    assert body.get("allowed_by_policy") is False


def test_process_kill_forbidden_never_executes(plat_client: TestClient) -> None:
    _ingest(plat_client, "kill-1", "process_kill_forbidden", category="unknown")
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "kill-1",
            "requested_action": "process_kill_forbidden",
        },
    )
    preview_id = prv.json()["preview_id"]
    ex = plat_client.post(
        "/platform/remediation/execute",
        json={
            "preview_id": preview_id,
            "confirmation_phrase": "KILL_PROCESS",
            "dry_run": False,
        },
    )
    assert ex.status_code == 200
    assert ex.json().get("result") == "blocked"


def test_firewall_reset_blocked_even_with_admin_and_phrase(plat_client: TestClient) -> None:
    _ingest(plat_client, "fw-1", "reset_firewall", category="firewall")
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "fw-1",
            "requested_action": "reset_firewall",
        },
    )
    preview_id = prv.json()["preview_id"]
    ex = plat_client.post(
        "/platform/remediation/execute",
        json={
            "preview_id": preview_id,
            "confirmation_phrase": "RUN_FIREWALL_RESET",
            "dry_run": False,
        },
    )
    assert ex.status_code == 200
    assert ex.json().get("result") == "blocked"


def test_adapter_disable_forbidden_blocked(plat_client: TestClient) -> None:
    _ingest(plat_client, "adp-1", "adapter_disable_forbidden", category="adapter")
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "adp-1",
            "requested_action": "adapter_disable_forbidden",
        },
    )
    assert prv.json().get("allowed_by_policy") is False


def test_preview_writes_audit_without_live_mutation(plat_client: TestClient, tmp_path) -> None:
    _ingest(plat_client, "audit-1", "inspect_proxy")
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "audit-1",
            "requested_action": "inspect_proxy",
        },
    )
    body = prv.json()
    assert body.get("audit_event_id")
    assert body.get("dry_run") is True
    audit_path = tmp_path / "audit.jsonl"
    assert audit_path.is_file()
    assert "remediation_preview" in audit_path.read_text(encoding="utf-8")


def test_operator_role_cannot_live_execute(monkeypatch, tmp_path) -> None:
    def target():
        return tmp_path

    monkeypatch.setattr("platform_core.storage.platform_data_dir", target)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", target)

    from backend.main import app

    operator_client = TestClient(
        app,
        headers={
            "X-Operator-Role": "operator",
            "X-Operator-Id": "pytest-operator",
        },
    )

    _ingest(operator_client, "op-1", "reset_dns")
    prv = operator_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "safety-ep",
            "failure_event_id": "op-1",
            "requested_action": "reset_dns",
        },
    )
    preview_id = prv.json()["preview_id"]
    ex = operator_client.post(
        "/platform/remediation/execute",
        json={
            "preview_id": preview_id,
            "confirmation_phrase": "RUN_DNS_RESET",
            "dry_run": False,
        },
    )
    assert ex.status_code == 403


def test_health_reports_dry_run_default(plat_client: TestClient) -> None:
    r = plat_client.get("/platform/health")
    assert r.status_code == 200
    assert r.json().get("remediation_default") == "dry_run"

"""Security and contract tests for agent-bound evidence ingestion."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.db import get_engine
from backend.db.models import EvidenceEvent, IncidentRecord
from backend.main import app

client = TestClient(app)


def _admin(tenant: str) -> dict[str, str]:
    return {
        "X-Api-Token": "test-token",
        "X-Api-Role": "admin",
        "X-Api-Tenant": tenant,
    }


def _enroll(tenant: str, hostname: str) -> dict:
    created = client.post(
        "/v1/organizations",
        json={"display_name": tenant},
        headers=_admin(tenant),
    )
    assert created.status_code == 201
    issued = client.post(
        "/v1/enrollment-tokens",
        json={"ttl_minutes": 30},
        headers=_admin(tenant),
    )
    assert issued.status_code == 201
    enrolled = client.post(
        "/v1/agents/enroll",
        json={
            "enrollment_token": issued.json()["enrollment_token"],
            "hostname": hostname,
            "agent_version": "0.2.0",
        },
    )
    assert enrolled.status_code == 201
    return enrolled.json()


def _proxy_evidence() -> dict:
    return {
        "source_event_id": "agent-src-001",
        "evidence_type": "proxy_state",
        "timestamp_utc": "2026-09-05T09:30:00Z",
        "raw_snapshot": {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:59081",
            "winhttp_direct_access": True,
            "localhost_port": 59081,
        },
        "normalized_fields": {"wininet_proxy_enabled": True},
        "evidence_tier": "T1_STATE_EVIDENCE",
        "limitations": ["Agent observation is not proof of compromise."],
    }


def test_agent_evidence_inherits_endpoint_and_tenant_and_reaches_endpoint_detail():
    enrolled = _enroll("org-a", "org-a-win11")
    secret = enrolled["agent_secret"]
    endpoint_id = enrolled["endpoint_id"]

    response = client.post(
        "/v1/agents/evidence",
        json=_proxy_evidence(),
        headers={"Authorization": f"Agent {secret}"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["endpoint_id"] == endpoint_id
    assert body["organization_id"] == "org-a"

    with Session(get_engine()) as session:
        evidence = session.exec(
            select(EvidenceEvent).where(EvidenceEvent.event_id == body["event_id"])
        ).first()
        assert evidence is not None
        assert evidence.endpoint_id == endpoint_id
        assert evidence.tenant_id == "org-a"

        incident = session.exec(
            select(IncidentRecord).where(IncidentRecord.evidence_event_id == body["event_id"])
        ).first()
        if incident is not None:
            assert incident.tenant_id == "org-a"

    detail = client.get(f"/v1/endpoints/{endpoint_id}", headers=_admin("org-a"))
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["endpoint_id"] == endpoint_id
    assert detail_body["evidence_state"]["event_id"] == body["event_id"]
    assert "liveness" in detail_body
    assert "evidence_state" in detail_body


def test_agent_cannot_override_endpoint_or_organization_scope():
    a = _enroll("org-a", "org-a-win11")
    b = _enroll("org-b", "org-b-win11")
    headers = {"Authorization": f"Agent {a['agent_secret']}"}

    wrong_endpoint = _proxy_evidence()
    wrong_endpoint["endpoint_id"] = b["endpoint_id"]
    denied_endpoint = client.post("/v1/agents/evidence", json=wrong_endpoint, headers=headers)
    assert denied_endpoint.status_code == 403

    wrong_org = _proxy_evidence()
    wrong_org["organization_id"] = "org-b"
    wrong_org["source_event_id"] = "agent-src-002"
    denied_org = client.post("/v1/agents/evidence", json=wrong_org, headers=headers)
    assert denied_org.status_code == 403


def test_endpoint_detail_is_tenant_isolated():
    a = _enroll("org-a", "org-a-win11")
    _enroll("org-b", "org-b-win11")

    own = client.get(f"/v1/endpoints/{a['endpoint_id']}", headers=_admin("org-a"))
    assert own.status_code == 200

    cross_tenant = client.get(f"/v1/endpoints/{a['endpoint_id']}", headers=_admin("org-b"))
    assert cross_tenant.status_code == 404

"""Contract and security-boundary tests for the P0 product control plane."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.db import get_engine
from backend.main import app
from backend.product_v1_models import AgentCredential, EnrollmentToken

client = TestClient(app)


def _admin(tenant: str) -> dict[str, str]:
    return {
        "X-Api-Token": "test-token",
        "X-Api-Role": "admin",
        "X-Api-Tenant": tenant,
    }


def _create_org_and_token(tenant: str = "org-a") -> tuple[str, str]:
    org = client.post(
        "/v1/organizations",
        json={"display_name": f"{tenant} Design Partner"},
        headers=_admin(tenant),
    )
    assert org.status_code == 201
    assert org.json()["organization_id"] == tenant

    issued = client.post(
        "/v1/enrollment-tokens",
        json={"ttl_minutes": 30},
        headers=_admin(tenant),
    )
    assert issued.status_code == 201
    return issued.json()["token_id"], issued.json()["enrollment_token"]


def test_p0_vertical_slice_enroll_heartbeat_and_list():
    _, token = _create_org_and_token("org-a")

    enrolled = client.post(
        "/v1/agents/enroll",
        json={
            "enrollment_token": token,
            "hostname": "win11-lab-01",
            "agent_version": "0.1.0",
            "os_name": "Windows 11",
            "os_version": "24H2",
        },
    )
    assert enrolled.status_code == 201
    endpoint_id = enrolled.json()["endpoint_id"]
    agent_secret = enrolled.json()["agent_secret"]
    assert endpoint_id.startswith("ep_")
    assert agent_secret.startswith("agt_")

    heartbeat = client.post(
        "/v1/agents/heartbeat",
        json={
            "heartbeat_id": "hb-contract-001",
            "agent_version": "0.1.0",
            "os_name": "Windows 11",
            "os_version": "24H2",
        },
        headers={"Authorization": f"Agent {agent_secret}"},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "ONLINE_UNASSESSED"
    assert heartbeat.json()["endpoint_id"] == endpoint_id

    fleet = client.get("/v1/endpoints", headers=_admin("org-a"))
    assert fleet.status_code == 200
    assert fleet.json()["total"] == 1
    assert fleet.json()["items"][0]["endpoint_id"] == endpoint_id
    assert fleet.json()["items"][0]["status"] == "ONLINE_UNASSESSED"


def test_enrollment_token_is_single_use_and_plaintext_is_not_stored():
    _, token = _create_org_and_token("org-a")
    payload = {"enrollment_token": token, "hostname": "win11-one"}
    first = client.post("/v1/agents/enroll", json=payload)
    assert first.status_code == 201
    second = client.post("/v1/agents/enroll", json=payload)
    assert second.status_code == 409

    agent_secret = first.json()["agent_secret"]
    with Session(get_engine()) as session:
        token_rows = list(session.exec(select(EnrollmentToken)))
        credential_rows = list(session.exec(select(AgentCredential)))
    assert token_rows
    assert credential_rows
    assert all(row.token_hash != token for row in token_rows)
    assert all(row.secret_hash != agent_secret for row in credential_rows)


def test_revoked_enrollment_token_cannot_enroll():
    token_id, token = _create_org_and_token("org-a")
    revoked = client.post(
        f"/v1/enrollment-tokens/{token_id}/revoke",
        headers=_admin("org-a"),
    )
    assert revoked.status_code == 200

    response = client.post(
        "/v1/agents/enroll",
        json={"enrollment_token": token, "hostname": "blocked-host"},
    )
    assert response.status_code == 401


def test_tenant_endpoint_listing_is_isolated():
    _, token = _create_org_and_token("org-a")
    enrolled = client.post(
        "/v1/agents/enroll",
        json={"enrollment_token": token, "hostname": "tenant-a-host"},
    )
    assert enrolled.status_code == 201

    # Create tenant B but do not enroll an endpoint there.
    created_b = client.post(
        "/v1/organizations",
        json={"display_name": "Tenant B"},
        headers=_admin("org-b"),
    )
    assert created_b.status_code == 201

    fleet_a = client.get("/v1/endpoints", headers=_admin("org-a"))
    fleet_b = client.get("/v1/endpoints", headers=_admin("org-b"))
    assert fleet_a.status_code == 200
    assert fleet_b.status_code == 200
    assert fleet_a.json()["total"] == 1
    assert fleet_b.json()["total"] == 0


def test_duplicate_heartbeat_is_idempotent():
    _, token = _create_org_and_token("org-a")
    enrolled = client.post(
        "/v1/agents/enroll",
        json={"enrollment_token": token, "hostname": "dup-heartbeat-host"},
    )
    secret = enrolled.json()["agent_secret"]
    headers = {"Authorization": f"Agent {secret}"}
    body = {"heartbeat_id": "hb-idempotent-001", "agent_version": "0.1.0"}

    first = client.post("/v1/agents/heartbeat", json=body, headers=headers)
    second = client.post("/v1/agents/heartbeat", json=body, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_proxy_request_proposes_non_mutating_tool() -> None:
    response = client.post("/api/agent/chat", json={"message": "Check proxy drift on this endpoint"})
    assert response.status_code == 200
    body = response.json()
    assert body["proposed_action"]["tool"]["name"] == "inspect_proxy"
    assert body["proposed_action"]["requires_approval"] is False
    assert body["evidence"]


def test_repair_request_requires_approval() -> None:
    response = client.post("/api/agent/chat", json={"message": "Please repair the endpoint"})
    assert response.status_code == 200
    action = response.json()["proposed_action"]
    assert action["requires_approval"] is True

    approval = client.post(f"/api/actions/{action['id']}/approve", json={"approved": True})
    assert approval.status_code == 200
    assert approval.json()["approved"] is True

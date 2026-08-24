from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.enterprise_ai_routes import router


def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def base_payload() -> dict:
    return {
        "request_id": "req-1",
        "asset_id": "endpoint-1",
        "action": "disable_wininet_proxy",
        "parameters": {
            "signals": {
                "confidence": 0.9,
                "evidence_tier": "OBSERVED_ONLY",
                "incident_type": "WININET_PROXY_DRIFT",
            }
        },
        "approved_by": "operator@example.com",
    }


def test_allowlisted_action_is_preview_only() -> None:
    response = client().post("/api/v1/remediation/execute", json=base_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"previewed", "blocked"}
    assert body["after_state"]["mutation_applied"] is False
    assert body["verification"]["mode"] == "dry_run"
    assert body["rollback_performed"] is False


def test_unknown_action_is_rejected() -> None:
    payload = base_payload()
    payload["action"] = "run_arbitrary_command"
    response = client().post("/api/v1/remediation/execute", json=payload)
    assert response.status_code == 403

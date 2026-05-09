from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from platform_core.product_contract import ProbeResult


@pytest.fixture()
def plat_client(monkeypatch, tmp_path):
    """Return a platform TestClient with JSONL storage isolated under pytest temp."""

    target = lambda: tmp_path
    monkeypatch.setattr("platform_core.storage.platform_data_dir", target)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", target)

    from backend.main import app

    return TestClient(
        app,
        headers={
            "X-Operator-Role": "admin",
            "X-Operator-Id": "pytest-platform",
        },
    )


def _fixture_probes(endpoint_id: str, *, include_live: bool = True) -> list[ProbeResult]:
    """Return deterministic probe rows for product-contract API tests."""

    _ = endpoint_id, include_live
    return [
        ProbeResult(name="dns_probe", status="ok", observed_value={"host": "www.microsoft.com"}),
        ProbeResult(name="tcp_443_probe", status="ok", observed_value="connected"),
        ProbeResult(name="https_probe", status="ok", observed_value={"tls_version": "TLSv1.3"}),
        ProbeResult(
            name="wininet_proxy_state",
            status="ok",
            observed_value={"proxy_enable": 1, "proxy_server": "127.0.0.1:57863"},
        ),
        ProbeResult(
            name="localhost_proxy_listener",
            status="ok",
            evidence_level="inference",
            observed_value={
                "candidate_actor": {"pid": 1234, "image": "devproxy.exe"},
                "proof_boundary": "listener_correlation_not_registry_writer",
            },
        ),
        ProbeResult(name="lkg_snapshot_available", status="warning", observed_value={"available": False}),
    ]


def test_health_contract_exposes_platform_safety_fields(plat_client: TestClient) -> None:
    response = plat_client.get("/platform/health")
    assert response.status_code == 200
    body = response.json()
    assert body["local_first_mode"] is True
    assert body["policy_mode"] == "safe_preview_default"
    assert body["remediation_default"] == "dry_run"
    assert body["audit_store_status"] == "available"


def test_diagnosis_run_separates_observation_inference_policy_and_audit(
    plat_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr("platform_core.product_contract.collect_probe_results", _fixture_probes)

    response = plat_client.post("/platform/diagnosis/run", json={"endpoint_id": "ep-product-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["endpoint_id"] == "ep-product-1"
    assert body["evidence_level"] == "inference"
    assert body["policy_result"]["decision"] == "preview_only"
    assert body["audit_event_id"]
    assert any(p["name"] == "wininet_proxy_state" for p in body["observations"])
    assert any("localhost proxy" in h for h in body["inferred_hypotheses"])
    assert body["evidence_level"] != "proof"

    latest = plat_client.get("/platform/diagnosis/latest")
    assert latest.status_code == 200
    assert latest.json()["diagnosis"]["run_id"] == body["run_id"]

    tail = plat_client.get("/platform/audit/tail?limit=5")
    assert tail.status_code == 200
    assert any(item.get("event_kind") == "diagnosis_run" for item in tail.json()["items"])


def test_endpoint_fleet_summary_is_backed_by_stored_diagnosis(
    plat_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr("platform_core.product_contract.collect_probe_results", _fixture_probes)
    run = plat_client.post("/platform/diagnosis/run", json={"endpoint_id": "ep-fleet-1"}).json()

    response = plat_client.get("/platform/endpoints")
    assert response.status_code == 200
    endpoints = response.json()["endpoints"]
    row = next(item for item in endpoints if item["endpoint_id"] == "ep-fleet-1")
    assert row["latest_diagnosis_id"] == run["run_id"]
    assert row["status"] == "drift_proxy"
    assert row["latest_risk_score"] > 0


def test_replay_uses_stored_observations_and_does_not_reprobe(
    plat_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr("platform_core.product_contract.collect_probe_results", _fixture_probes)
    run_id = plat_client.post("/platform/diagnosis/run", json={"endpoint_id": "ep-replay-1"}).json()["run_id"]

    def fail_if_called(endpoint_id: str, *, include_live: bool = True) -> list[ProbeResult]:
        raise AssertionError("replay must not collect live probes")

    monkeypatch.setattr("platform_core.product_contract.collect_probe_results", fail_if_called)
    replay = plat_client.get(f"/platform/replay/{run_id}")
    assert replay.status_code == 200
    body = replay.json()
    assert body["replay_mode"] == "stored_observations_only"
    assert body["live_reprobe"] is False
    assert body["recomputed"]["evidence_level"] == "inference"


def test_remediation_contract_defaults_to_dry_run_and_appends_audit(
    plat_client: TestClient,
) -> None:
    event = {
        "event_id": "product-remediate-1",
        "endpoint_id": "ep-remediate-1",
        "severity": "medium",
        "category": "dns",
        "confidence": 0.77,
        "summary": "fixture dns issue",
        "recommended_action_key": "reset_dns",
    }
    assert plat_client.post("/platform/failure-events/ingest", json=event).status_code == 200
    preview = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "ep-remediate-1",
            "failure_event_id": "product-remediate-1",
            "requested_action": "reset_dns",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["action_id"] == preview_body["preview_id"]
    assert preview_body["decision"] == "preview_only"
    assert preview_body["audit_event_id"]

    execute = plat_client.post(
        "/platform/remediation/execute",
        json={"preview_id": preview_body["preview_id"], "confirmation_phrase": "RUN_DNS_RESET"},
    )
    assert execute.status_code == 200
    execute_body = execute.json()
    assert execute_body["result"] == "dry_run"
    assert execute_body["dry_run"] is True
    assert execute_body["decision"] == "preview_only"
    assert execute_body["audit_event_id"]


def test_high_risk_preview_contract_is_blocked(plat_client: TestClient) -> None:
    event = {
        "event_id": "product-firewall-1",
        "endpoint_id": "ep-risk-1",
        "severity": "high",
        "category": "firewall",
        "confidence": 0.91,
        "summary": "fixture firewall issue",
        "recommended_action_key": "reset_firewall",
    }
    plat_client.post("/platform/failure-events/ingest", json=event)
    response = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "ep-risk-1",
            "failure_event_id": "product-firewall-1",
            "requested_action": "reset_firewall",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["decision"] == "blocked"
    assert body["reason"] == "high_risk_blocked_from_platform"


def test_lkg_and_rollback_preview_are_preview_only(plat_client: TestClient) -> None:
    snapshot = plat_client.post(
        "/platform/lkg/snapshot",
        json={"endpoint_id": "ep-lkg-1", "snapshot": {"ProxyEnable": 0, "ProxyServer": ""}},
    )
    assert snapshot.status_code == 200
    snapshot_id = snapshot.json()["snapshot_id"]

    lkg = plat_client.get("/platform/lkg/ep-lkg-1")
    assert lkg.status_code == 200
    assert lkg.json()["available"] is True

    preview = plat_client.post(
        "/platform/rollback/preview",
        json={"endpoint_id": "ep-lkg-1", "target_snapshot_id": snapshot_id, "fields": ["ProxyEnable"]},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["decision"] == "preview_only"
    assert body["dry_run"] is True
    assert body["allowed"] is False


def test_agent_next_step_is_suggestion_only(plat_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("platform_core.product_contract.collect_probe_results", _fixture_probes)
    run_id = plat_client.post("/platform/diagnosis/run", json={"endpoint_id": "ep-agent-1"}).json()["run_id"]

    response = plat_client.post(
        "/platform/agent/next-step",
        json={"run_id": run_id, "goal": "explain_risk"},
    )
    assert response.status_code == 200
    body = response.json()
    safe_next_steps = {
        "run_diagnosis",
        "run_proxy_disable_preview",
        "inspect_node_process",
        "run_registry_writer_proof",
        "restart_browser",
        "collect_lkg",
        "compare_proxy_config",
        "review_audit",
    }
    assert body["next_step"] in safe_next_steps
    assert body["policy_boundary"] == "recommendation_only_no_mutation"
    assert "process_kill" in body["blocked_actions"]
    assert "firewall_reset" in body["blocked_actions"]
    assert body["confidence"] > 0

    invalid = plat_client.post("/platform/agent/next-step", json={"run_id": run_id, "goal": "repair"})
    assert invalid.status_code == 422

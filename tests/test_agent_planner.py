"""Agent next-step planner: bounded recommendations, no mutation, audit clarity."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from platform_core.agent_planner import (
    BLOCKED_ACTIONS,
    AgentNextStep,
    plan_next_step,
)


def _diag(observations: list[dict[str, Any]], *, confidence: float = 0.7, proof: str = "inconclusive") -> SimpleNamespace:
    return SimpleNamespace(
        observations=[SimpleNamespace(name=o["name"], status=o.get("status"), observed_value=o.get("observed_value")) for o in observations],
        confidence=confidence,
        proof_status=proof,
        inferred_hypotheses=["browser_proxy_path_issue"],
        evidence_level="inference",
        endpoint_id="endpoint-x",
        run_id="run-1",
    )


def test_planner_returns_recommendation_only_response_with_blocked_actions() -> None:
    diag = _diag(
        [
            {"name": "wininet_proxy_state", "status": "ok", "observed_value": {"proxy_server": "127.0.0.1:57863", "proxy_enable": 1}},
            {"name": "https_probe", "status": "failed"},
        ]
    )
    plan = plan_next_step(diag)
    assert isinstance(plan, AgentNextStep)
    assert plan.policy_boundary == "recommendation_only_no_mutation"
    assert "process_kill" in plan.blocked_actions
    assert plan.next_step == "run_registry_writer_proof"


def test_planner_never_returns_mutating_action_id() -> None:
    diag = _diag(
        [
            {"name": "wininet_proxy_state", "status": "ok", "observed_value": {"proxy_server": "127.0.0.1:8888", "proxy_enable": 1}},
            {"name": "https_probe", "status": "failed"},
        ],
        proof="confirmed",
        confidence=0.9,
    )
    for goal in (
        "suggest_next_probe",
        "rank_hypotheses",
        "explain_risk",
        "recommend_preview_action",
        "summarize_audit",
        "identify_missing_evidence",
    ):
        plan = plan_next_step(diag, goal=goal)  # type: ignore[arg-type]
        assert plan.next_step not in BLOCKED_ACTIONS, f"goal {goal} produced blocked action"
        assert "execute" not in plan.next_step.lower()


def test_planner_handles_missing_diagnosis() -> None:
    plan = plan_next_step(None)
    assert plan.next_step == "run_diagnosis"
    assert plan.policy_boundary == "recommendation_only_no_mutation"


def test_planner_recommends_proxy_disable_preview_when_high_confidence() -> None:
    diag = _diag(
        [
            {"name": "wininet_proxy_state", "status": "ok", "observed_value": {"proxy_server": "10.0.0.5:3128", "proxy_enable": 1}},
            {"name": "https_probe", "status": "failed"},
        ],
        confidence=0.85,
        proof="confirmed",
    )
    plan = plan_next_step(diag, goal="recommend_preview_action")
    assert plan.next_step == "run_proxy_disable_preview"


def test_planner_identifies_missing_evidence() -> None:
    diag = _diag([{"name": "dns_probe", "status": "ok"}])
    plan = plan_next_step(diag, goal="identify_missing_evidence")
    assert plan.next_step == "run_diagnosis"
    assert "wininet_proxy_state" in plan.reason


def test_existing_backend_route_still_returns_recommendation_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_BYPASS_USER_ID", "pytest-user")
    monkeypatch.setenv("AUTH_BYPASS_EMAIL", "pytest@example.com")
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    response = client.post("/platform/agent/next-step", json={"goal": "suggest_next_probe"})
    assert response.status_code == 200
    body = response.json()
    assert body["policy_boundary"] == "recommendation_only_no_mutation"
    assert "process_kill" in body["blocked_actions"]

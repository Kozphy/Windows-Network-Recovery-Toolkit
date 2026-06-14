"""Agent orchestrator integration tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.agent.agent_orchestrator import AgentAskRequest, build_plan, handle_ask
from src.platform_core.agent.audit import read_agent_audit_tail
from src.platform_core.agent.intent import AgentIntent, classify_intent
from src.platform_core.agent.rbac import AgentRole, normalize_role
from src.platform_core.agent.tool_registry import ToolContext, invoke_tool


FIXTURE = str(Path("case_studies/cs1_wininet_proxy_drift/fixture.json"))


def test_orchestrator_diagnose_proxy_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    audit_path = tmp_path / "agent-actions.jsonl"
    resp = handle_ask(
        AgentAskRequest(
            user_id="eng1",
            role="viewer",
            message="ERR_PROXY_CONNECTION_FAILED",
            fixture=FIXTURE,
        ),
        audit_log_path=audit_path,
    )
    assert resp.intent == "DIAGNOSE_PROXY"
    assert resp.allowed
    assert resp.tool_called == "diagnose_proxy"
    assert resp.audit_event_id
    assert resp.dry_run is True
    rows = read_agent_audit_tail(log_path=audit_path)
    assert len(rows) == 1
    assert rows[0]["intent"] == "DIAGNOSE_PROXY"


def test_plan_includes_tools_without_execution() -> None:
    intent = classify_intent("proxy broken")
    plan = build_plan(intent, normalize_role("analyst"))
    assert plan.allowed
    assert plan.steps
    assert all(s.dry_run for s in plan.steps)


def test_tool_registry_fixture_safe() -> None:
    result = invoke_tool("diagnose_proxy", ToolContext(fixture_path=FIXTURE, dry_run=True))
    assert result.evidence.get("classification") == "DEAD_PROXY_CONFIG"
    assert result.limitations


def test_remediation_preview_never_mutates() -> None:
    preview = invoke_tool("remediation_preview", ToolContext(fixture_path=FIXTURE, dry_run=True))
    assert preview.evidence.get("no_changes_made") is True
    assert preview.evidence.get("dry_run") is True

"""Agent policy safety tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.agent.agent_orchestrator import (
    AgentAskRequest,
    AgentExecutePreviewRequest,
    check_safety_policy,
    handle_ask,
    handle_execute_preview,
)
from src.platform_core.agent.intent import AgentIntent


def test_dangerous_execution_blocked_by_policy() -> None:
    ok, reason = check_safety_policy(
        AgentIntent.PREVIEW_REMEDIATION,
        message="reset firewall and kill process now",
    )
    assert not ok
    assert "blocked" in reason


def test_viewer_remediation_denied(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    resp = handle_ask(
        AgentAskRequest(
            user_id="u1",
            role="viewer",
            message="fix it disable proxy",
            fixture=str(Path("case_studies/cs1_wininet_proxy_drift/fixture.json")),
        ),
        audit_log_path=tmp_path / "agent-actions.jsonl",
    )
    assert not resp.allowed
    assert resp.status == "denied"


def test_operator_remediation_preview_dry_run_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    resp = handle_execute_preview(
        AgentExecutePreviewRequest(
            user_id="op1",
            role="operator",
            fixture=str(Path("case_studies/cs1_wininet_proxy_drift/fixture.json")),
            dry_run=False,
        ),
        audit_log_path=tmp_path / "agent-actions.jsonl",
    )
    assert resp.allowed
    assert resp.no_changes_made
    assert resp.preview.get("dry_run") is True


def test_agent_response_includes_limitations(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    resp = handle_ask(
        AgentAskRequest(
            user_id="a1",
            role="analyst",
            message="browser cannot connect proxy broken",
            fixture=str(Path("case_studies/cs1_wininet_proxy_drift/fixture.json")),
        ),
        audit_log_path=tmp_path / "agent-actions.jsonl",
    )
    assert resp.limitations
    assert any("Observation" in lim or "proof" in lim.lower() for lim in resp.limitations)


def test_unknown_intent_safe_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    resp = handle_ask(
        AgentAskRequest(user_id="u2", role="viewer", message="tell me a joke"),
        audit_log_path=tmp_path / "agent-actions.jsonl",
    )
    assert resp.intent == "UNKNOWN"
    assert resp.status == "unknown"
    assert resp.evidence == {}

"""Evidence-gated AI agent orchestrator — no autonomous destructive actions."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.platform_core.agent.audit import append_agent_audit
from src.platform_core.agent.intent import INTENT_TO_TOOL, AgentIntent, classify_intent
from src.platform_core.agent.rbac import AgentRole, check_rbac, normalize_role
from src.platform_core.agent.response_builder import build_answer, recommended_next_action
from src.platform_core.agent.tool_registry import ToolContext, ToolResult, invoke_tool
from src.platform_core.agent.usage_limits import get_usage_limiter

AgentStatus = Literal["ok", "denied", "rate_limited", "unknown", "preview_only"]

_DEFAULT_LIMITATIONS = [
    "Observation is not proof.",
    "Correlation is not causation.",
    "Confidence is ordinal, not exact probability.",
    "Policy permission is not a safety guarantee.",
]


class AgentAskRequest(BaseModel):
    user_id: str = "anonymous"
    team_id: str = "default"
    role: str = "viewer"
    message: str
    url: str | None = None
    fixture: str | None = None
    dry_run: bool = True


class AgentAskResponse(BaseModel):
    intent: str
    allowed: bool
    status: AgentStatus
    answer: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    recommended_next_action: str = ""
    audit_event_id: str | None = None
    tool_called: str | None = None
    dry_run: bool = True


class AgentPlanStep(BaseModel):
    tool: str
    purpose: str
    dry_run: bool = True


class AgentPlanResponse(BaseModel):
    intent: str
    allowed: bool
    steps: list[AgentPlanStep] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AgentExecutePreviewRequest(BaseModel):
    user_id: str = "anonymous"
    team_id: str = "default"
    role: str = "operator"
    intent: str = "PREVIEW_REMEDIATION"
    fixture: str | None = None
    dry_run: bool = True


class AgentExecutePreviewResponse(BaseModel):
    allowed: bool
    status: AgentStatus
    preview: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    audit_event_id: str | None = None
    no_changes_made: bool = True


def _agent_forces_dry_run(request_dry_run: bool) -> bool:
    """Agent layer never performs live mutations — always effective dry_run."""
    _ = request_dry_run
    return True


def check_safety_policy(intent: AgentIntent, *, message: str) -> tuple[bool, str]:
    """Block dangerous execution patterns even for admin role."""
    lower = message.lower()
    dangerous = (
        "kill process",
        "reset firewall",
        "disable adapter",
        "run shell",
        "execute without confirmation",
        "skip confirmation",
        "dry-run false",
        "dry_run false",
    )
    for phrase in dangerous:
        if phrase in lower:
            return False, f"blocked dangerous pattern: {phrase}"
    if intent == AgentIntent.UNKNOWN:
        return True, "unknown intent — safe fallback only"
    return True, "policy ok"


def build_plan(intent: AgentIntent, role: AgentRole) -> AgentPlanResponse:
    allowed, _ = check_rbac(role, intent)
    tool_name = INTENT_TO_TOOL.get(intent)
    steps: list[AgentPlanStep] = []
    if allowed and tool_name:
        steps.append(
            AgentPlanStep(
                tool=tool_name,
                purpose=f"Collect evidence for {intent.value}",
                dry_run=True,
            )
        )
    elif intent == AgentIntent.DIAGNOSE_PROXY and allowed:
        steps = [
            AgentPlanStep(tool="proxy_status", purpose="Observe WinINET state", dry_run=True),
            AgentPlanStep(tool="diagnose_proxy", purpose="Run structured proof envelope", dry_run=True),
        ]
    limitations = list(_DEFAULT_LIMITATIONS)
    if not allowed:
        limitations.append("RBAC denied — plan contains no executable steps.")
    return AgentPlanResponse(intent=intent.value, allowed=allowed, steps=steps, limitations=limitations)


def handle_ask(request: AgentAskRequest, *, audit_log_path: Any = None) -> AgentAskResponse:
    intent = classify_intent(request.message)
    role = normalize_role(request.role)
    effective_dry_run = _agent_forces_dry_run(request.dry_run)
    request_id = f"req-{uuid.uuid4().hex[:12]}"

    limiter = get_usage_limiter()
    rate_ok, rate_reason = limiter.check(request.user_id)
    if not rate_ok:
        rid = append_agent_audit(
            user_id=request.user_id,
            team_id=request.team_id,
            role=role.value,
            intent=intent.value,
            tool_called=None,
            allowed=False,
            dry_run=effective_dry_run,
            limitations=_DEFAULT_LIMITATIONS,
            reason=rate_reason,
            request_id=request_id,
            log_path=audit_log_path,
        )
        return AgentAskResponse(
            intent=intent.value,
            allowed=False,
            status="rate_limited",
            answer=f"Rate limited: {rate_reason}",
            limitations=_DEFAULT_LIMITATIONS,
            recommended_next_action="retry later",
            audit_event_id=rid,
            dry_run=effective_dry_run,
        )

    rbac_ok, rbac_reason = check_rbac(role, intent)
    policy_ok, policy_reason = check_safety_policy(intent, message=request.message)
    allowed = rbac_ok and policy_ok

    tool_result: ToolResult | None = None
    tool_name = INTENT_TO_TOOL.get(intent)
    limitations = list(_DEFAULT_LIMITATIONS)

    if allowed and tool_name and intent != AgentIntent.UNKNOWN:
        ctx = ToolContext(
            url=request.url,
            fixture_path=request.fixture,
            dry_run=effective_dry_run,
        )
        tool_result = invoke_tool(tool_name, ctx)
        limitations.extend(tool_result.limitations)

    reason = rbac_reason if not rbac_ok else policy_reason
    answer = build_answer(intent, tool_result, allowed=allowed and intent != AgentIntent.UNKNOWN, reason=reason)
    status: AgentStatus = "ok" if allowed and intent != AgentIntent.UNKNOWN else (
        "denied" if not allowed else "unknown"
    )

    rid = append_agent_audit(
        user_id=request.user_id,
        team_id=request.team_id,
        role=role.value,
        intent=intent.value,
        tool_called=tool_name,
        allowed=allowed and intent != AgentIntent.UNKNOWN,
        dry_run=effective_dry_run,
        limitations=limitations,
        reason=reason,
        request_id=request_id,
        log_path=audit_log_path,
    )

    return AgentAskResponse(
        intent=intent.value,
        allowed=allowed and intent != AgentIntent.UNKNOWN,
        status=status,
        answer=answer,
        evidence=tool_result.evidence if tool_result else {},
        limitations=limitations,
        recommended_next_action=recommended_next_action(intent, tool_result),
        audit_event_id=rid,
        tool_called=tool_name,
        dry_run=effective_dry_run,
    )


def handle_execute_preview(
    request: AgentExecutePreviewRequest,
    *,
    audit_log_path: Any = None,
) -> AgentExecutePreviewResponse:
    """Run preview-safe tools only — never live mutation."""
    try:
        intent = AgentIntent(request.intent)
    except ValueError:
        intent = AgentIntent.PREVIEW_REMEDIATION

    role = normalize_role(request.role)
    effective_dry_run = True  # forced
    rbac_ok, rbac_reason = check_rbac(role, intent)

    if not rbac_ok or intent != AgentIntent.PREVIEW_REMEDIATION:
        rid = append_agent_audit(
            user_id=request.user_id,
            team_id=request.team_id,
            role=role.value,
            intent=intent.value,
            tool_called=None,
            allowed=False,
            dry_run=True,
            limitations=_DEFAULT_LIMITATIONS,
            reason=rbac_reason if not rbac_ok else "execute-preview limited to remediation preview",
            log_path=audit_log_path,
        )
        return AgentExecutePreviewResponse(
            allowed=False,
            status="denied",
            limitations=_DEFAULT_LIMITATIONS + [rbac_reason],
            audit_event_id=rid,
            no_changes_made=True,
        )

    ctx = ToolContext(fixture_path=request.fixture, dry_run=True)
    preview = invoke_tool("remediation_preview", ctx)
    rid = append_agent_audit(
        user_id=request.user_id,
        team_id=request.team_id,
        role=role.value,
        intent=intent.value,
        tool_called="remediation_preview",
        allowed=True,
        dry_run=True,
        limitations=preview.limitations + _DEFAULT_LIMITATIONS,
        reason="preview-only execution",
        log_path=audit_log_path,
    )
    return AgentExecutePreviewResponse(
        allowed=True,
        status="preview_only",
        preview=preview.evidence,
        limitations=preview.limitations + _DEFAULT_LIMITATIONS,
        audit_event_id=rid,
        no_changes_made=True,
    )

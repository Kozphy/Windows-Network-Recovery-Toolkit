"""FastAPI routes for evidence-gated AI agent governance."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.platform_auth import get_platform_principal
from platform_core.rbac import DemoPrincipal

from src.platform_core.agent.agent_orchestrator import (
    AgentAskRequest,
    AgentExecutePreviewRequest,
    build_plan,
    handle_ask,
    handle_execute_preview,
)
from src.platform_core.agent.audit import read_agent_audit_tail
from src.platform_core.agent.intent import AgentIntent, classify_intent
from src.platform_core.agent.rbac import normalize_role

router = APIRouter(prefix="/agent", tags=["agent"])


def _resolve_role(body_role: str, principal: DemoPrincipal) -> str:
    """Prefer explicit body role; fall back to platform header role."""
    if body_role and body_role != "viewer":
        return body_role
    mapping = {
        "admin": "admin",
        "operator": "operator",
        "security_auditor": "analyst",
        "viewer": "viewer",
    }
    return mapping.get(principal.role, body_role or "viewer")


@router.post("/ask")
def agent_ask(
    body: AgentAskRequest,
    principal: DemoPrincipal = Depends(get_platform_principal),
) -> dict:
    """Natural-language triage over safe evidence tools only."""
    body.role = _resolve_role(body.role, principal)
    body.dry_run = True
    result = handle_ask(body)
    return result.model_dump()


@router.post("/plan")
def agent_plan(
    body: AgentAskRequest,
    principal: DemoPrincipal = Depends(get_platform_principal),
) -> dict:
    """Return proposed tool calls without executing them."""
    body.role = _resolve_role(body.role, principal)
    intent = classify_intent(body.message)
    role = normalize_role(body.role)
    plan = build_plan(intent, role)
    return plan.model_dump()


@router.post("/execute-preview")
def agent_execute_preview(
    body: AgentExecutePreviewRequest,
    principal: DemoPrincipal = Depends(get_platform_principal),
) -> dict:
    """Preview-safe actions only — never live host mutation."""
    body.role = _resolve_role(body.role, principal)
    body.dry_run = True
    result = handle_execute_preview(body)
    return result.model_dump()


@router.get("/audit")
def agent_audit(
    principal: DemoPrincipal = Depends(get_platform_principal),
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict:
    """Recent agent audit events — admin only."""
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="agent audit restricted to admin")
    rows = read_agent_audit_tail(limit=limit)
    return {"count": len(rows), "items": rows}

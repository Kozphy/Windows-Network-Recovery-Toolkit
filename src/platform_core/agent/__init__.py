"""Evidence-gated AI agent governance layer."""

from src.platform_core.agent.agent_orchestrator import (
    AgentAskRequest,
    AgentAskResponse,
    AgentExecutePreviewRequest,
    AgentExecutePreviewResponse,
    AgentPlanResponse,
    build_plan,
    handle_ask,
    handle_execute_preview,
)
from src.platform_core.agent.audit import AGENT_AUDIT_LOG, append_agent_audit, read_agent_audit_tail
from src.platform_core.agent.intent import AgentIntent, classify_intent
from src.platform_core.agent.rbac import AgentRole, check_rbac, normalize_role

__all__ = [
    "AGENT_AUDIT_LOG",
    "AgentAskRequest",
    "AgentAskResponse",
    "AgentExecutePreviewRequest",
    "AgentExecutePreviewResponse",
    "AgentIntent",
    "AgentPlanResponse",
    "AgentRole",
    "append_agent_audit",
    "build_plan",
    "check_rbac",
    "classify_intent",
    "handle_ask",
    "handle_execute_preview",
    "normalize_role",
    "read_agent_audit_tail",
]

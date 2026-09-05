"""Enterprise AI adapter for policy-gated remediation previews.

This router is deliberately non-mutating. It translates the AgentGuard execution
contract into the toolkit's existing remediation planner while preserving the
repository invariant that registry changes are never performed silently.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.platform_core.remediation.planner import plan_proxy_drift_remediation

router = APIRouter(prefix="/api/v1/remediation", tags=["enterprise-ai"])

_ALLOWED_ACTIONS = frozenset({"disable_wininet_proxy"})


class EnterpriseRemediationRequest(BaseModel):
    schema_version: str = "1.0"
    request_id: str = Field(min_length=1, max_length=160)
    asset_id: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=160)
    parameters: dict[str, Any] = Field(default_factory=dict)
    approved_by: str = Field(min_length=1, max_length=200)


class EnterpriseRemediationResponse(BaseModel):
    execution_id: str
    status: Literal["previewed", "blocked"]
    before_state: dict[str, Any] = Field(default_factory=dict)
    after_state: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    rollback_performed: bool = False


@router.post("/execute", response_model=EnterpriseRemediationResponse)
def execute_enterprise_remediation(
    payload: EnterpriseRemediationRequest,
) -> EnterpriseRemediationResponse:
    """Create an approved, policy-gated remediation preview for AgentGuard.

    The endpoint name matches the cross-service execution contract, but this
    implementation remains preview-only until a separately reviewed mutation
    executor is introduced. Unknown actions are rejected rather than passed to a
    shell or registry command.
    """
    if payload.action not in _ALLOWED_ACTIONS:
        raise HTTPException(status_code=403, detail="Action is not in the enterprise allowlist")

    signals = dict(payload.parameters.get("signals") or {})
    signals.setdefault("endpoint_id", payload.asset_id)
    signals.setdefault("incident_type", "WININET_PROXY_DRIFT")

    plan = plan_proxy_drift_remediation(
        incident_id=payload.request_id,
        recommended_action=payload.action,
        signals=signals,
        prior_proxy_enable=int(payload.parameters.get("prior_proxy_enable", 1)),
        prior_proxy_server=str(payload.parameters.get("prior_proxy_server", "")),
        dry_run=True,
    )

    policy_gate = dict(plan.get("policy_gate") or {})
    outcome = str(policy_gate.get("outcome", "BLOCK"))
    blocked = outcome == "BLOCK"
    pre_snapshot = dict((plan.get("rollback_preview") or {}).get("pre_change_snapshot") or {})

    return EnterpriseRemediationResponse(
        execution_id=f"preview-{uuid.uuid4().hex[:12]}",
        status="blocked" if blocked else "previewed",
        before_state=pre_snapshot,
        after_state={
            "mutation_applied": False,
            "approved_by": payload.approved_by,
            "policy_outcome": outcome,
        },
        verification={
            "mode": "dry_run",
            "can_execute": bool((plan.get("approval") or {}).get("can_execute", False)),
            "blocked_reasons": plan.get("blocked_reasons", []),
            "rollback_plan_present": bool(plan.get("rollback_plan")),
        },
        rollback_performed=False,
    )

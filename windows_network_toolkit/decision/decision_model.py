"""Decision result models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high", "critical"]


class IncidentType(StrEnum):
    NO_PROXY = "NO_PROXY"
    KNOWN_DEV_PROXY = "KNOWN_DEV_PROXY"
    KNOWN_SECURITY_TOOL = "KNOWN_SECURITY_TOOL"
    UNKNOWN_LOCAL_PROXY = "UNKNOWN_LOCAL_PROXY"
    SUSPICIOUS_PROXY = "SUSPICIOUS_PROXY"
    POSSIBLE_MITM_RISK = "POSSIBLE_MITM_RISK"
    WININET_PROXY_DRIFT = "WININET_PROXY_DRIFT"
    REGISTRY_REWRITER_OBSERVED = "REGISTRY_REWRITER_OBSERVED"
    WRITER_AND_LISTENER_MATCH = "WRITER_AND_LISTENER_MATCH"
    DNS_OK_BROWSER_FAIL = "DNS_OK_BROWSER_FAIL"
    PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS = "PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS"


class DecisionResult(BaseModel):
    decision_id: str
    incident_id: str
    incident_type: IncidentType
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel = "medium"
    recommended_action: str = ""
    requires_confirmation: bool = True
    reasoning: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    rollback_plan: str = ""
    human_review_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

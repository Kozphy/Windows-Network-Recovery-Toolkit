"""Canonical Multi-Domain Decision Platform models.

Single source of truth for: Event → Evidence → Hypothesis → Decision → Policy → Outcome.
Endpoint reliability models (``platform_core.evidence_model``, remediation) remain separate.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DomainName = Literal["windows", "security", "cloud", "infrastructure", "market"]

PolicyStatus = Literal[
    "ALLOW_RESEARCH",
    "PREVIEW_ONLY",
    "BLOCK_LOW_CONFIDENCE",
    "BLOCK_AUTONOMOUS_ACTION",
    "BLOCK_DESTRUCTIVE_ACTION",
]

ActionType = Literal["research", "preview", "recommendation", "execute_like"]
EvidenceType = Literal["observation", "correlation", "proof", "counter_evidence"]
Severity = Literal["low", "medium", "high", "critical"]


class NormalizedEvent(BaseModel):
    event_id: str
    domain: DomainName
    category: str
    title: str
    timestamp_utc: str
    severity: Severity = "medium"
    observations: list[dict[str, Any]] = Field(default_factory=list)
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    evidence_id: str
    event_id: str
    type: EvidenceType = "observation"
    description: str
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)
    confidence_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    source: str = ""
    timestamp_utc: str = ""


class Hypothesis(BaseModel):
    hypothesis_id: str
    event_id: str
    title: str
    explanation: str
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class DecisionOption(BaseModel):
    decision_id: str
    event_id: str
    title: str
    action_type: ActionType = "recommendation"
    expected_benefit: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_score: float = Field(default=0.2, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    alternatives: list[str] = Field(default_factory=list)
    policy_status: PolicyStatus = "PREVIEW_ONLY"
    explanation: str = ""
    final_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    """Policy gate result — permission is not a safety guarantee."""

    status: PolicyStatus
    execute_allowed: bool = False
    preview_allowed: bool = True
    reasons: list[str] = Field(default_factory=list)
    explanation: str = ""


class DecisionOutcome(BaseModel):
    outcome_id: str
    decision_id: str
    success: bool
    observed_result: str = ""
    cost_score: float = Field(default=0.0, ge=0.0, le=1.0)
    time_to_resolution_seconds: float = Field(default=0.0, ge=0.0)
    lessons_learned: str = ""

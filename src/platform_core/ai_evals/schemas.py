"""Pydantic schemas for the AI evals feedback loop.

Defines typed structures for fixture cases (including embedded ``ModelOutput``),
per-case eval results, policy decisions, and aggregated suite reports.

All model outputs are read from fixture JSON — this package never calls a live LLM API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .failure_taxonomy import EvalPolicyGate, FailureLabel

ConfidenceLevel = Literal["very_low", "low", "medium", "high"]
EvalStatus = Literal["pass", "fail", "partial"]
SeverityLevel = Literal["low", "medium", "high"]


class ModelOutput(BaseModel):
    text: str = ""
    json_payload: dict[str, Any] | None = None
    citations: list[str] = Field(default_factory=list)
    latency_ms: float | None = None
    token_cost_usd: float | None = None


class EvalCase(BaseModel):
    case_id: str
    task_type: str = "support_rag"
    prompt: str
    expected_answer: str | None = None
    expected_facts: list[str] = Field(default_factory=list)
    retrieved_context: list[str] = Field(default_factory=list)
    model_output: ModelOutput
    format_spec: str | None = None
    require_citations: bool = False
    max_latency_ms: float | None = None
    max_token_cost_usd: float | None = None
    expected_failure_labels: list[str] = Field(default_factory=list)
    expected_policy: str | None = None
    severity: SeverityLevel = "medium"
    notes: str = ""


class FailureSignal(BaseModel):
    label: FailureLabel
    detail: str = ""
    severity: SeverityLevel = "medium"


class EvalPolicyDecision(BaseModel):
    gate: EvalPolicyGate
    rationale: str = ""
    requires_human_review: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    recommendation: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class EvalResult(BaseModel):
    case_id: str
    task_type: str = "support_rag"
    status: EvalStatus
    failure_labels: list[FailureLabel] = Field(default_factory=list)
    failure_signals: list[FailureSignal] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = "medium"
    policy_decision: EvalPolicyDecision
    checks_run: list[str] = Field(default_factory=list)
    recommendation: str = ""


class EvalReport(BaseModel):
    schema_version: str = "ai_evals.v1"
    total_cases: int = 0
    pass_count: int = 0
    fail_count: int = 0
    partial_count: int = 0
    results: list[EvalResult] = Field(default_factory=list)
    taxonomy_distribution: dict[str, int] = Field(default_factory=dict)
    policy_distribution: dict[str, int] = Field(default_factory=dict)
    high_risk_cases: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    positioning: str = (
        "Portfolio-grade evaluation harness for structured model quality signals — "
        "not a formal model safety certification or audit opinion."
    )
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

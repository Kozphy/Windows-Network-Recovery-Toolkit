"""Schemas for bounded, policy-gated offline optimization."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .failure_taxonomy import EvalPolicyGate


class OptimizationCandidate(BaseModel):
    candidate_id: str
    parent_id: str | None = None
    parameters: dict[str, Any]
    generation_reason: str
    iteration: int = Field(ge=0)


class CandidateEvaluation(BaseModel):
    candidate: OptimizationCandidate
    fitness_score: float = Field(ge=0.0, le=1.0)
    blocked: bool = False
    requires_human_review: bool = True
    policy_gate: EvalPolicyGate
    improvement_over_baseline: float
    accepted: bool = False
    rejection_reason: str | None = None

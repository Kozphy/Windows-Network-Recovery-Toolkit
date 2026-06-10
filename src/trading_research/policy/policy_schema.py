"""MVP policy decisions — live trading never approved."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PolicyDecision(StrEnum):
    APPROVE_RESEARCH_ONLY = "APPROVE_RESEARCH_ONLY"
    BLOCK = "BLOCK"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"


class PolicyResult(BaseModel):
    decision: PolicyDecision
    rationale: str
    blocked_reasons: list[str] = Field(default_factory=list)

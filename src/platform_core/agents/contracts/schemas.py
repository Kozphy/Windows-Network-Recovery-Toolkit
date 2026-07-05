"""Pydantic agent output contracts — deterministic interchange, not autonomous execution."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceAgentOutput(BaseModel):
    event_id: str
    endpoint_id: str
    evidence_type: str
    evidence_tier: str = "T1_STATE_EVIDENCE"
    raw_snapshot: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class ClassificationAgentOutput(BaseModel):
    incident_id: str
    primary_classification: str
    proof_tier: str
    confidence: float = Field(ge=0.0, le=1.0)
    secondary_signals: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RootCauseAgentOutput(BaseModel):
    incident_id: str
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RiskAssessmentAgentOutput(BaseModel):
    incident_id: str
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: str
    human_review_recommended: bool = False
    limitations: list[str] = Field(default_factory=list)


class ControlValidationAgentOutput(BaseModel):
    incident_id: str
    control_tests: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ReportingAgentOutput(BaseModel):
    report_type: str = "executive"
    kpis: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)

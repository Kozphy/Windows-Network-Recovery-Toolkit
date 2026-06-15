"""Enterprise risk assessment models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import RiskLevel


class RiskAssessment(BaseModel):
    risk_id: str
    finding_id: str
    threat_id: str
    inherent_risk: RiskLevel
    residual_risk: RiskLevel
    likelihood: RiskLevel
    impact: RiskLevel
    control_effectiveness: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)


class RiskRegisterEntry(BaseModel):
    risk_id: str
    title: str
    inherent_risk: RiskLevel
    residual_risk: RiskLevel
    owner: str
    status: str = "open"
    linked_findings: list[str] = Field(default_factory=list)

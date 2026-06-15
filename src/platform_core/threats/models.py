"""Threat layer models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import Criticality, RiskLevel


class Threat(BaseModel):
    threat_id: str
    name: str
    description: str
    attack_vector: str
    likelihood: RiskLevel = RiskLevel.MEDIUM
    impact: RiskLevel = RiskLevel.MEDIUM
    asset_ids: list[str] = Field(default_factory=list)

"""Website risk scoring models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WebsiteRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class WebsiteRiskEvidence(BaseModel):
    signal: str
    observed: str
    weight: float = 0.0
    detail: str = ""


class WebsiteRiskResult(BaseModel):
    assessment_id: str
    timestamp_utc: str
    url: str
    final_url: str = ""
    risk_level: WebsiteRiskLevel = WebsiteRiskLevel.UNKNOWN
    score: float = 0.0
    evidence: list[WebsiteRiskEvidence] = Field(default_factory=list)
    reputation_plugins_used: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

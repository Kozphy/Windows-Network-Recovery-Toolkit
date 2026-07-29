"""Governance contracts for optional machine-learning recommendations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RiskFeatures(BaseModel):
    """Validated tabular features derived from evidence, controls, and outcomes."""

    proxy_enabled: bool
    listener_found: bool
    direct_probe_ok: bool | None = None
    proxy_probe_ok: bool | None = None
    proof_tier: int = Field(ge=0, le=5)
    failed_control_count: int = Field(ge=0)
    partial_control_count: int = Field(ge=0)
    recurrence_count: int = Field(ge=0)
    previous_restoration_verified: bool = False
    time_to_restore_seconds: float | None = Field(default=None, ge=0)

    def as_vector(self) -> list[float]:
        """Stable feature order shared by baseline and PyTorch models."""
        return [
            float(self.proxy_enabled),
            float(self.listener_found),
            -1.0 if self.direct_probe_ok is None else float(self.direct_probe_ok),
            -1.0 if self.proxy_probe_ok is None else float(self.proxy_probe_ok),
            self.proof_tier / 5.0,
            min(self.failed_control_count, 10) / 10.0,
            min(self.partial_control_count, 10) / 10.0,
            min(self.recurrence_count, 10) / 10.0,
            float(self.previous_restoration_verified),
            min(self.time_to_restore_seconds or 0.0, 86400.0) / 86400.0,
        ]


class ModelRecommendation(BaseModel):
    """Advisory model output with explicit governance boundaries."""

    schema_version: Literal["model_recommendation.v1"] = "model_recommendation.v1"
    incident_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    risk_score: float = Field(ge=0.0, le=1.0)
    review_priority: Literal["LOW", "MEDIUM", "HIGH"]
    explanation: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    execution_authority: Literal["NONE"] = "NONE"
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def preserve_governance_boundary(self) -> "ModelRecommendation":
        required = "Model output is advisory and is not proof, causation, or execution authority."
        if required not in self.limitations:
            self.limitations.append(required)
        return self

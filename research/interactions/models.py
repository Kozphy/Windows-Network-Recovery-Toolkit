"""Data models for factorial interaction-effect experiments."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InteractionCase(BaseModel):
    """Single factorial observation in an interaction experiment."""

    experiment_id: str
    case_id: str
    factor_a_name: str
    factor_b_name: str
    x1: int = Field(ge=0, le=1)
    x2: int = Field(ge=0, le=1)
    replicate: int = 0
    fixture: dict[str, Any]
    y_failure: int = Field(ge=0, le=1, description="Ground-truth binary failure (designed).")
    y_severity: float = Field(
        ge=0.0,
        le=1.0,
        description="Ground-truth ordinal severity for interaction contrast.",
    )
    limitations: list[str] = Field(default_factory=list)


class InteractionObservation(InteractionCase):
    """Case plus platform-observed outcomes."""

    y_platform_failure: int = Field(ge=0, le=1)
    y_platform_severity: float = Field(ge=0.0, le=1.0)
    incident_class: str = ""
    classifier_confidence: float = 0.0


class CellSummary(BaseModel):
    """Aggregated outcome for one 2x2 factorial cell."""

    x1: int
    x2: int
    n: int
    mean_y_failure: float
    mean_y_severity: float
    mean_platform_failure: float
    mean_platform_severity: float


class InteractionEffectEstimate(BaseModel):
    """Main and interaction effect estimates for one outcome variable."""

    outcome: str
    main_effect_x1: float
    main_effect_x2: float
    interaction_effect: float
    lpm_beta_0: float = 0.0
    lpm_beta_1: float = 0.0
    lpm_beta_2: float = 0.0
    lpm_beta_3: float = 0.0
    sample_size: int
    cell_summaries: list[CellSummary] = Field(default_factory=list)
    ci_lower: float | None = None
    ci_upper: float | None = None
    ci_method: str | None = None
    effect_size_label: str = "additive_contrast"
    limitations: list[str] = Field(default_factory=list)


class InteractionAnalysisResult(BaseModel):
    """Full analysis for one factorial experiment."""

    experiment_id: str
    factor_a_name: str
    factor_b_name: str
    description: str
    git_sha: str = "unknown"
    dataset_digest: str = ""
    random_seed: int = 42
    sample_size: int = 0
    effects: list[InteractionEffectEstimate] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class InteractionRunManifest(BaseModel):
    """Top-level manifest for an interaction-effects run."""

    schema_version: str = "interaction_effects.v1"
    experiment_count: int = 0
    case_count: int = 0
    git_sha: str = "unknown"
    random_seed: int = 42
    timestamp_utc: str = ""
    experiments: list[str] = Field(default_factory=list)

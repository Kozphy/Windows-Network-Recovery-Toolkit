"""SLO and reliability metric models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReliabilityMetrics(BaseModel):
    browser_path_success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    proxy_drift_events_per_day: float = Field(ge=0.0, default=0.0)
    mean_time_to_detect_seconds: float | None = None
    mean_time_to_recover_seconds: float | None = None
    remediation_stickiness_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0, default=0.0)

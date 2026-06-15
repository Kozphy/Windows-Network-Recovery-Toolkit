"""Findings management models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import Severity


class Finding(BaseModel):
    finding_id: str
    severity: Severity
    description: str
    impacted_assets: list[str] = Field(default_factory=list)
    control_id: str
    test_id: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    limitations: list[str] = Field(default_factory=list)

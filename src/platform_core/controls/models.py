"""Enterprise control library models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import ControlType


class Control(BaseModel):
    control_id: str
    control_name: str
    objective_id: str
    objective: str
    control_owner: str
    control_type: ControlType
    frequency: str = "continuous"
    evidence_requirements: list[str] = Field(default_factory=list)

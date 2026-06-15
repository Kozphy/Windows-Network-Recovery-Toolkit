"""Business objective layer — every control traces to an objective."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import Criticality


class BusinessObjective(BaseModel):
    id: str
    name: str
    description: str
    owner: str
    criticality: Criticality = Criticality.HIGH
    regulatory_mapping: list[str] = Field(default_factory=list)

"""Enterprise asset layer."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import Criticality


class Asset(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    owner: str
    classification: str = "internal"
    criticality: Criticality = Criticality.MEDIUM
    metadata: dict[str, str] = Field(default_factory=dict)

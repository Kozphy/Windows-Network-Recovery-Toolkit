"""Market event types — MVP: PRICE_BREAKOUT and VOLUME_SPIKE only."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConfidenceOrdinal(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EventType(StrEnum):
    PRICE_BREAKOUT = "PRICE_BREAKOUT"
    VOLUME_SPIKE = "VOLUME_SPIKE"


class MarketEvent(BaseModel):
    """Detected market event — observation, not proof of edge."""

    timestamp: str
    event_type: EventType
    symbol: str
    evidence: str
    confidence_score: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence_score")
    @classmethod
    def _ordinal_only(cls, v: str) -> str:
        allowed = {m.value for m in ConfidenceOrdinal}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"confidence_score must be ordinal {allowed}, got {v!r}")
        return upper

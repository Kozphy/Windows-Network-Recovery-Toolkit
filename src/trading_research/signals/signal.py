"""Trading signal model — MVP: LONG entries only."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class SignalDirection(StrEnum):
    LONG = "LONG"


class TradingSignal(BaseModel):
    timestamp: str
    symbol: str
    direction: SignalDirection = SignalDirection.LONG
    source_event: str
    rationale: str
    confidence_score: str
    invalidation_rule: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("confidence_score")
    @classmethod
    def _ordinal_only(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"confidence_score must be ordinal {allowed}")
        return upper

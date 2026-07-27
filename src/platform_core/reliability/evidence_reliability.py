"""Evidence reliability dimensions kept separate from classifier confidence."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


class ReliabilityBand(StrEnum):
    RELIABLE = "reliable"
    USABLE_WITH_LIMITATIONS = "usable_with_limitations"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class EvidenceReliability(BaseModel):
    source_integrity: int = Field(ge=0, le=100)
    freshness: int = Field(ge=0, le=100)
    collection_reproducibility: int = Field(ge=0, le=100)
    coverage: int = Field(ge=0, le=100)
    contradiction_penalty: int = Field(default=0, ge=0, le=100)
    limitations: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def score(self) -> int:
        base = (
            self.source_integrity
            + self.freshness
            + self.collection_reproducibility
            + self.coverage
        ) / 4
        return max(0, min(100, round(base - self.contradiction_penalty)))

    @computed_field
    @property
    def overall_band(self) -> ReliabilityBand:
        if self.score >= 80:
            return ReliabilityBand.RELIABLE
        if self.score >= 60:
            return ReliabilityBand.USABLE_WITH_LIMITATIONS
        if self.score >= 35:
            return ReliabilityBand.WEAK
        return ReliabilityBand.INSUFFICIENT

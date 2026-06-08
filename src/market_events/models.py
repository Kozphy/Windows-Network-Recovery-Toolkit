"""Domain models for the Market Event Intelligence Engine (research-only)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventCategory(StrEnum):
    MACRO = "MACRO"
    REGULATORY = "REGULATORY"
    TOKEN_UNLOCK = "TOKEN_UNLOCK"
    PROTOCOL_UPGRADE = "PROTOCOL_UPGRADE"
    GOVERNANCE = "GOVERNANCE"
    ETF_FLOW = "ETF_FLOW"
    STABLECOIN_FLOW = "STABLECOIN_FLOW"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"
    EXCHANGE_LISTING = "EXCHANGE_LISTING"
    LIQUIDITY_EVENT = "LIQUIDITY_EVENT"


class VolatilityExpectation(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DirectionBias(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class ResearchPolicyStatus(StrEnum):
    ALLOW_RESEARCH = "ALLOW_RESEARCH"
    PREVIEW_ONLY = "PREVIEW_ONLY"
    BLOCK_TRADE_EXECUTION = "BLOCK_TRADE_EXECUTION"
    BLOCK_LOW_CONFIDENCE = "BLOCK_LOW_CONFIDENCE"


class MarketEvent(BaseModel):
    event_id: str
    title: str
    category: EventCategory
    timestamp_utc: str
    affected_assets: list[str] = Field(default_factory=list)
    expected_volatility: VolatilityExpectation = VolatilityExpectation.MEDIUM
    direction_bias: DirectionBias = DirectionBias.UNKNOWN
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source: str = ""
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetImpact(BaseModel):
    asset: str
    volatility_contribution: float = 0.0
    direction_contribution: float = 0.0
    rationale: str = ""


class EventEvidence(BaseModel):
    node_id: str
    label: str
    kind: str
    detail: str = ""
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    supports_thesis: bool | None = None


class SignalScore(BaseModel):
    event_id: str
    volatility_score: int = Field(ge=0, le=100)
    direction_score: int = Field(ge=-100, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    main_drivers: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    asset_impacts: list[AssetImpact] = Field(default_factory=list)
    policy_status: ResearchPolicyStatus = ResearchPolicyStatus.ALLOW_RESEARCH


class TradeThesis(BaseModel):
    event_id: str
    headline: str
    summary: str
    direction_bias: DirectionBias
    volatility_expectation: VolatilityExpectation
    confidence: float
    risk_notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Research draft only — not financial advice. No trade execution is performed or authorized."
    )
    policy_status: ResearchPolicyStatus = ResearchPolicyStatus.ALLOW_RESEARCH


class ThesisOutcome(StrEnum):
    TRUE = "true"
    FALSE = "false"
    PARTIAL = "partial"


class PostEventReview(BaseModel):
    event_id: str
    expected_volatility: VolatilityExpectation
    actual_price_change_pct: float
    actual_volume_change_pct: float
    actual_volatility: VolatilityExpectation
    thesis_correct: ThesisOutcome
    lessons_learned: str = ""
    scoring_adjustment_suggestion: str = ""


class EvidenceTree(BaseModel):
    event_id: str
    observation: str
    candidate_interpretation: str
    supporting_evidence: list[EventEvidence] = Field(default_factory=list)
    contradicting_evidence: list[EventEvidence] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    final_research_note: str = ""

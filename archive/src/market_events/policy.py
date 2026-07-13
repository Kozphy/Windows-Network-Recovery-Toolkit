"""Research policy guardrails — no trade execution, confidence and source gates."""

from __future__ import annotations

from .models import MarketEvent, ResearchPolicyStatus, SignalScore


def evaluate_research_policy(
    event: MarketEvent,
    *,
    request_execution: bool = False,
) -> ResearchPolicyStatus:
    if request_execution:
        return ResearchPolicyStatus.BLOCK_TRADE_EXECUTION
    if not (event.source or "").strip():
        return ResearchPolicyStatus.PREVIEW_ONLY
    if event.confidence < 0.4:
        return ResearchPolicyStatus.BLOCK_LOW_CONFIDENCE
    return ResearchPolicyStatus.ALLOW_RESEARCH


def apply_policy_to_score(score: SignalScore, status: ResearchPolicyStatus) -> SignalScore:
    notes = list(score.risk_notes)
    if status == ResearchPolicyStatus.BLOCK_TRADE_EXECUTION:
        notes.append("Trade execution requests are always blocked in research mode.")
    elif status == ResearchPolicyStatus.PREVIEW_ONLY:
        notes.append("Missing or empty source — preview-only research signal.")
    elif status == ResearchPolicyStatus.BLOCK_LOW_CONFIDENCE:
        notes.append("Confidence below 0.4 — low-confidence research gate.")
    return score.model_copy(update={"policy_status": status, "risk_notes": notes})

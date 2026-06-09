"""Unified deterministic decision scoring (all domains)."""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.models import DecisionOption, EvidenceItem, Hypothesis, NormalizedEvent

CONFIDENCE_BONUS_SCALE = 0.25
POLICY_PENALTIES = {
    "ALLOW_RESEARCH": 0.0,
    "PREVIEW_ONLY": 0.05,
    "BLOCK_AUTONOMOUS_ACTION": 0.15,
    "BLOCK_LOW_CONFIDENCE": 0.25,
    "BLOCK_DESTRUCTIVE_ACTION": 0.4,
}


@dataclass
class RankedDecision:
    decision: DecisionOption
    benefit: float
    risk: float
    confidence: float
    confidence_bonus: float
    policy_penalty: float
    final_score: float
    explanation: str


def score_decision(decision: DecisionOption, *, hypothesis_confidence: float) -> RankedDecision:
    bonus = round(hypothesis_confidence * CONFIDENCE_BONUS_SCALE, 4)
    penalty = POLICY_PENALTIES.get(decision.policy_status, 0.1)
    raw = decision.expected_benefit - decision.risk_score + bonus - penalty
    final = round(max(0.0, min(1.0, raw)), 4)
    explanation = (
        f"{decision.decision_id}: benefit={decision.expected_benefit:.2f} - risk={decision.risk_score:.2f} "
        f"+ bonus={bonus:.2f} - penalty={penalty:.2f} => {final:.2f}"
    )
    scored = decision.model_copy(
        update={"confidence": hypothesis_confidence, "final_score": final, "explanation": explanation}
    )
    return RankedDecision(
        decision=scored,
        benefit=decision.expected_benefit,
        risk=decision.risk_score,
        confidence=hypothesis_confidence,
        confidence_bonus=bonus,
        policy_penalty=penalty,
        final_score=final,
        explanation=explanation,
    )


def rank_decisions(
    event: NormalizedEvent,
    ranked_hypotheses: list[Hypothesis],
    evidence: list[EvidenceItem],
    candidates: list[DecisionOption],
) -> list[RankedDecision]:
    _ = event, evidence
    top_conf = ranked_hypotheses[0].confidence if ranked_hypotheses else 0.4
    scored = [score_decision(d, hypothesis_confidence=top_conf) for d in candidates]
    scored.sort(key=lambda r: (-r.final_score, r.decision.decision_id))
    return scored

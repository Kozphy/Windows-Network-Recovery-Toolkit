from __future__ import annotations

from uuid import uuid4

from .models import DecisionRequest, EvidenceKind, OptionAssessment, Recommendation
from .policy import GovernancePolicy


def _weighted_utility(request: DecisionRequest, scores: dict[str, float]) -> float:
    total_weight = sum(c.weight for c in request.criteria)
    return sum(c.weight * scores[c.name] for c in request.criteria) / total_weight


def _evidence_coverage(request: DecisionRequest) -> float:
    if not request.evidence:
        return 0.0
    known = [e for e in request.evidence if e.kind is EvidenceKind.FACT]
    return sum(e.confidence for e in known) / len(request.evidence)


def analyze(request: DecisionRequest, policy: GovernancePolicy | None = None) -> Recommendation:
    coverage = _evidence_coverage(request)
    assessments: list[OptionAssessment] = []

    for option in request.options:
        utility = _weighted_utility(request, option.scores)
        adjusted = (
            utility
            - request.risk_penalty * option.risk
            - request.uncertainty_penalty * option.uncertainty
        )
        assessments.append(
            OptionAssessment(
                option=option.name,
                utility_score=round(utility, 4),
                adjusted_score=round(adjusted, 4),
                risk=option.risk,
                uncertainty=option.uncertainty,
            )
        )

    assessments.sort(key=lambda item: item.adjusted_score, reverse=True)
    best = assessments[0]
    runner_up = assessments[1]
    margin = max(0.0, best.adjusted_score - runner_up.adjusted_score)
    confidence = min(1.0, 0.5 * coverage + 0.5 * min(1.0, margin * 2.0))

    recommendation = Recommendation(
        decision_id=str(uuid4()),
        requester=request.requester,
        domain=request.domain,
        question=request.question,
        recommended_option=best.option,
        confidence=round(confidence, 4),
        evidence_coverage=round(coverage, 4),
        assessments=assessments,
        assumptions=[e.statement for e in request.evidence if e.kind is EvidenceKind.ASSUMPTION],
        unknowns=[e.statement for e in request.evidence if e.kind is EvidenceKind.UNKNOWN],
    )
    recommendation.policy_flags = (policy or GovernancePolicy()).evaluate(recommendation)
    return recommendation

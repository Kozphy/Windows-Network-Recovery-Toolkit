from __future__ import annotations

from dataclasses import dataclass

from .models import Recommendation


@dataclass(frozen=True)
class GovernancePolicy:
    min_evidence_coverage: float = 0.35
    min_confidence: float = 0.20
    high_risk_threshold: float = 0.75
    max_unknowns_without_flag: int = 1

    def evaluate(self, recommendation: Recommendation) -> list[str]:
        flags: list[str] = []
        if recommendation.evidence_coverage < self.min_evidence_coverage:
            flags.append("LOW_EVIDENCE_COVERAGE")
        if recommendation.confidence < self.min_confidence:
            flags.append("LOW_CONFIDENCE")
        if len(recommendation.unknowns) > self.max_unknowns_without_flag:
            flags.append("MATERIAL_UNKNOWNS")
        selected = next(
            item for item in recommendation.assessments
            if item.option == recommendation.recommended_option
        )
        if selected.risk >= self.high_risk_threshold:
            flags.append("HIGH_RISK_RECOMMENDATION")
        return flags


def approval_allowed(recommendation: Recommendation) -> tuple[bool, str | None]:
    blocking = {"LOW_EVIDENCE_COVERAGE", "HIGH_RISK_RECOMMENDATION"}
    hit = blocking.intersection(recommendation.policy_flags)
    if hit:
        return False, f"policy blocks approval: {', '.join(sorted(hit))}"
    return True, None

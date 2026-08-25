from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Decision:
    action: str
    approved: bool
    reason: str
    confidence: float
    requires_human_review: bool


class DecisionEngine:
    def decide(
        self,
        *,
        proposed_action: str,
        confidence: float,
        min_confidence: float,
        allowed_actions: Iterable[str],
        require_human_review: bool,
        human_approved: bool = False,
    ) -> Decision:
        allowed = set(allowed_actions)
        if proposed_action not in allowed:
            return Decision(proposed_action, False, "action_not_allowed", confidence, require_human_review)
        if confidence < min_confidence:
            return Decision(proposed_action, False, "confidence_below_threshold", confidence, require_human_review)
        if require_human_review and not human_approved:
            return Decision(proposed_action, False, "human_review_required", confidence, True)
        return Decision(proposed_action, True, "approved", confidence, require_human_review)

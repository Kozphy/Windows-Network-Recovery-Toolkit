"""Canonical policy engine."""

from __future__ import annotations

from typing import Any

from src.platform_core.contracts import Decision, EvidenceBundle, PolicyEvaluation
from src.platform_core.evidence.guards import (
    ProofInputs,
    can_unlock_destructive_remediation,
    proof_inputs_from_signals,
)
from src.platform_core.evidence.tiers import EvidenceTier, tier_rank
from src.platform_core.policy.actions import is_destructive, normalize_action

from .outcomes import PolicyOutcomeName


def evaluate_policy(
    *,
    decision: Decision,
    bundle: EvidenceBundle,
    requested_action: str,
    proof: ProofInputs | None = None,
    operator_context: dict[str, Any] | None = None,
    dry_run: bool = True,
) -> PolicyEvaluation:
    operator_context = operator_context or {}
    proof = proof or proof_inputs_from_signals(
        {item.signal: item.observed_value for item in bundle.items}
    )
    tier: EvidenceTier = bundle.tier
    action = normalize_action(requested_action)
    blocked: list[str] = []
    outcome: PolicyOutcomeName = "PREVIEW_ONLY"
    requires_approval = False
    requires_rollback = False

    destructive = is_destructive(action)

    if destructive and not can_unlock_destructive_remediation(tier, proof):
        outcome = "BLOCK"
        blocked.append(action)
        blocked.append("destructive_without_final_causation")

    elif destructive:
        outcome = "REQUIRE_HUMAN_APPROVAL"
        requires_approval = True
        requires_rollback = True

    elif tier_rank(tier) < tier_rank("PROVEN_NETWORK_IMPACT"):
        outcome = "PREVIEW_ONLY"

    else:
        outcome = "ALLOW" if not dry_run else "PREVIEW_ONLY"

    if decision.requires_human_review:
        outcome = "REQUIRE_HUMAN_APPROVAL"
        requires_approval = True

    allowed = outcome in {"ALLOW", "PREVIEW_ONLY", "REQUIRE_HUMAN_APPROVAL"}

    return PolicyEvaluation(
        evaluation_id=f"peval-{decision.decision_id}",
        decision_id=decision.decision_id,
        timestamp_utc=decision.timestamp_utc,
        requested_action=action,
        evidence_tier=tier,
        outcome=outcome,
        allowed=allowed and action not in blocked,
        requires_approval=requires_approval,
        requires_rollback_plan=requires_rollback,
        blocked_reasons=blocked,
        rationale=(
            "Policy permission is not a safety guarantee. "
            "Destructive actions require FINAL_CAUSATION, preview, approval, audit, validation, rollback."
        ),
    )

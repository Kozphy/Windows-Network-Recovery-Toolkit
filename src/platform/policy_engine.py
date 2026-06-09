"""Unified policy guardrails — research / preview only, all domains."""

from __future__ import annotations

from src.platform.models import DecisionOption, NormalizedEvent, PolicyDecision, PolicyStatus

DESTRUCTIVE = frozenset(
    {"kill", "delete", "wipe", "disable_adapter", "reset_firewall", "execute", "trade", "liquidate"}
)
EXECUTE_LIKE = frozenset({"execute_like", "execute"})


def evaluate_policy(
    event: NormalizedEvent,
    decision: DecisionOption,
    *,
    confidence: float,
) -> PolicyDecision:
    title = decision.title.lower()
    if any(tok in title for tok in DESTRUCTIVE):
        return PolicyDecision(
            status="BLOCK_DESTRUCTIVE_ACTION",
            execute_allowed=False,
            preview_allowed=False,
            reasons=["destructive_token"],
            explanation="Destructive action blocked.",
        )
    if confidence < 0.4:
        return PolicyDecision(
            status="BLOCK_LOW_CONFIDENCE",
            execute_allowed=False,
            preview_allowed=True,
            reasons=["low_confidence"],
            explanation=f"Confidence {confidence:.2f} below 0.4.",
        )
    if not event.source:
        return PolicyDecision(
            status="PREVIEW_ONLY",
            execute_allowed=False,
            preview_allowed=True,
            reasons=["missing_source"],
            explanation="Missing source — preview only.",
        )
    if decision.action_type in EXECUTE_LIKE:
        return PolicyDecision(
            status="BLOCK_AUTONOMOUS_ACTION",
            execute_allowed=False,
            preview_allowed=False,
            reasons=["execute_like"],
            explanation="Autonomous execution forbidden.",
        )
    if decision.action_type == "research":
        return PolicyDecision(
            status="ALLOW_RESEARCH",
            execute_allowed=False,
            preview_allowed=True,
            reasons=["research_only"],
            explanation="Research permitted; not execution permission.",
        )
    return PolicyDecision(
        status="PREVIEW_ONLY",
        execute_allowed=False,
        preview_allowed=True,
        reasons=["default_gate"],
        explanation="Default preview-only gate.",
    )


def apply_policy(
    event: NormalizedEvent,
    decisions: list[DecisionOption],
    *,
    confidence: float,
) -> list[DecisionOption]:
    out: list[DecisionOption] = []
    for dec in decisions:
        pol = evaluate_policy(event, dec, confidence=confidence)
        out.append(
            dec.model_copy(
                update={
                    "policy_status": pol.status,
                    "explanation": pol.explanation,
                }
            )
        )
    return out


# Backward-compatible aliases
apply_policy_to_decisions = apply_policy


def validate_decision_policy(
    event: NormalizedEvent,
    decision: DecisionOption,
    *,
    confidence: float,
) -> tuple[PolicyStatus, str]:
    pol = evaluate_policy(event, decision, confidence=confidence)
    return pol.status, pol.explanation

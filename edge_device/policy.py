"""Policy gate for simulated edge-device remediation actions (ALLOW / PREVIEW / BLOCK).

Module responsibility:
    Map (hypothesis, proof, impact, requested_action, confirmation, conflicts) to a typed
    :class:`~platform_core.reasoning_models.PolicyDecision`, reusing the canonical reason-code
    vocabulary in :mod:`platform_core.policy_v2`.

System placement:
    Final gate of :mod:`edge_device.reasoning`. Mirrors
    ``platform_core.reasoning_engine.evaluate_reasoning_policy`` so the edge layer behaves
    identically to the proxy/browser layer: no auto-execute, preview before remediation,
    destructive actions always blocked.

Decision intent:
    Decide whether the edge reasoning chain is strong enough to ALLOW a known low-risk,
    reversible action, downgrade to PREVIEW for operator review, or BLOCK destructive paths.
    This function never executes anything.

Key invariants:
    * Tokens in :data:`EDGE_DESTRUCTIVE_TOKENS` (and platform always-blocked actions) BLOCK
      unconditionally, regardless of confidence or proof.
    * Only keys in :data:`EDGE_SAFE_ACTIONS` may ever reach ALLOW, and only with CONFIRMED
      proof + explicit confirmation + no conflicting signals + non-critical impact.
    * High/critical impact without CONFIRMED proof is forced to PREVIEW (defense-in-depth).

How to verify or audit:
    Re-run with identical inputs — output is deterministic. ``reason_codes`` always carries
    the rule that fired; an ``ALLOW`` outcome alongside any ``*REQUIRES*``/``UNPROVEN`` code
    indicates a regression.
"""

from __future__ import annotations

from platform_core import policy_v2 as pv2
from platform_core.reasoning_models import PolicyDecision, ProofResult

# Allowlisted, reversible, low-risk simulated edge actions.
EDGE_SAFE_ACTIONS: frozenset[str] = frozenset(
    {
        "switch_to_cpu_fallback",
        "reduce_inference_load",
        "restart_inference_runtime",
        "clear_inference_cache",
    }
)

# Substrings that must never auto-execute on an edge device (simulation still blocks them).
EDGE_DESTRUCTIVE_TOKENS: tuple[str, ...] = (
    "flash_firmware",
    "overwrite_firmware",
    "factory_reset",
    "reset_device",
    "disable_thermal",
    "disable_thermal_protection",
    "force_overclock",
    "overclock",
    "disable_sensor",
    "wipe",
    "format",
    "delete",
    "kill",
    "arbitrary_shell",
)

EDGE_CONFIRMATION_PHRASE = "APPLY_EDGE_SAFE_ACTION"


def _edge_blocked_actions(outcome: str, action: str | None) -> list[str]:
    """Return blocked action keys for an edge decision (platform set + edge destructive)."""
    blocked = list(pv2.ALWAYS_BLOCKED_ACTIONS) + list(EDGE_DESTRUCTIVE_TOKENS)
    norm = (action or "").strip().lower()
    if outcome == "BLOCK" and norm and norm not in blocked:
        blocked.append(norm)
    return list(dict.fromkeys(blocked))


def evaluate_edge_policy(
    *,
    hypothesis: str,
    state_transition: str,
    proof_result: ProofResult,
    confidence: float,
    impact_level: str,
    requested_action: str | None,
    explicit_confirmation: bool = False,
    conflicting_signals: bool = False,
) -> PolicyDecision:
    """Gate a requested edge remediation action into ALLOW / PREVIEW / BLOCK.

    Args:
        hypothesis: Accepted hypothesis id (catalog id or nominal/indeterminate).
        state_transition: Final state label for the run (audit context only).
        proof_result: Optional simulated proof outcome; ``CONFIRMED`` is required for ALLOW.
        confidence: Ordinal hypothesis confidence in ``[0.0, 1.0]`` (not a probability).
        impact_level: ``low`` | ``medium`` | ``high`` | ``critical``; high/critical force
            PREVIEW unless proof is ``CONFIRMED``.
        requested_action: Optional remediation key. ``None`` -> diagnostic-only PREVIEW.
            Destructive tokens -> BLOCK. Non-allowlisted -> BLOCK.
        explicit_confirmation: ``True`` when the operator typed the documented phrase.
        conflicting_signals: ``True`` when contradictory observations are present.

    Returns:
        Immutable :class:`PolicyDecision` with outcome, reason codes, blocked actions, and
        recommended next steps.

    Audit Notes:
        The blocked-action list always includes the platform always-blocked set plus edge
        destructive tokens, so audit consumers can assert no destructive key was authorized
        regardless of outcome.
    """
    action = (requested_action or "").strip().lower() or None
    proof_status = proof_result.status

    if action and any(token in action for token in EDGE_DESTRUCTIVE_TOKENS):
        return PolicyDecision(
            source="edge_policy",
            outcome="BLOCK",
            requested_action=action,
            hypothesis=hypothesis,
            state_transition=state_transition,
            evidence_level="proof" if proof_status == "CONFIRMED" else "inferred",
            proof_status=proof_status,
            confidence=confidence,
            trust_level="low" if conflicting_signals else "medium",
            impact_level=impact_level,  # type: ignore[arg-type]
            reason_codes=[pv2.DESTRUCTIVE_ACTION_BLOCKED],
            blocked_actions=_edge_blocked_actions("BLOCK", action),
            limitations=[
                "Firmware flash, factory reset, thermal-protection disable, overclock, and "
                "sensor disable are never auto-executed by the edge layer."
            ],
            recommended_next_steps=["Use manual, hardware-vendor-guided recovery after preserving evidence."],
        )

    if not action:
        return PolicyDecision(
            source="edge_policy",
            outcome="PREVIEW",
            requested_action=None,
            hypothesis=hypothesis,
            state_transition=state_transition,
            evidence_level="proof" if proof_status == "CONFIRMED" else "inferred",
            proof_status=proof_status,
            confidence=confidence,
            trust_level="low" if conflicting_signals else "medium",
            impact_level=impact_level,  # type: ignore[arg-type]
            reason_codes=[pv2.DIAGNOSTIC_ONLY],
            blocked_actions=_edge_blocked_actions("PREVIEW", None),
            recommended_next_steps=["Run a safe remediation action in preview if intervention is needed."],
        )

    if action not in EDGE_SAFE_ACTIONS:
        return PolicyDecision(
            source="edge_policy",
            outcome="BLOCK",
            requested_action=action,
            hypothesis=hypothesis,
            state_transition=state_transition,
            evidence_level="proof" if proof_status == "CONFIRMED" else "inferred",
            proof_status=proof_status,
            confidence=confidence,
            trust_level="low" if conflicting_signals else "medium",
            impact_level=impact_level,  # type: ignore[arg-type]
            reason_codes=[pv2.UNKNOWN_ACTION],
            blocked_actions=_edge_blocked_actions("BLOCK", action),
            limitations=["Only allowlisted low-risk edge actions can pass policy."],
            recommended_next_steps=["Choose an allowlisted safe action or continue diagnostics."],
        )

    reason_codes: list[str] = []
    limitations: list[str] = []
    trust_level = "low" if conflicting_signals else ("high" if proof_status == "CONFIRMED" else "medium")
    evidence_level = "proof" if proof_status == "CONFIRMED" else "validated"

    if conflicting_signals:
        reason_codes.append(pv2.CONFLICTING_SIGNALS)
        limitations.append("Conflicting observations reduce trust; live execution is not allowed.")
        outcome = "PREVIEW"
    elif proof_status == "CONFIRMED" and explicit_confirmation:
        reason_codes.append(pv2.CONFIRMED_SAFE_TIER_WITH_CONFIRMATION)
        reason_codes.append(pv2.SAFE_TIER_ACTION)
        outcome = "ALLOW"
    else:
        reason_codes.append(pv2.REQUIRES_OPERATOR_CONFIRMATION)
        reason_codes.append(pv2.PREVIEW_UNTIL_PROOF)
        outcome = "PREVIEW"

    # Defense-in-depth: re-assert PREVIEW downgrades rather than only annotating codes.
    if impact_level in ("high", "critical") and proof_status != "CONFIRMED":
        reason_codes.append(pv2.HIGH_IMPACT_UNPROVEN)
        outcome = "PREVIEW"
    if impact_level == "critical" and trust_level != "high":
        reason_codes.append(pv2.CRITICAL_IMPACT_LOW_TRUST)
        outcome = "PREVIEW"
    if proof_status != "CONFIRMED":
        reason_codes.append(pv2.HIGH_CONFIDENCE_UNPROVEN)
        outcome = "PREVIEW"

    reason_codes.append(pv2.REQUIRES_TYPED_CONFIRMATION)

    return PolicyDecision(
        source="edge_policy",
        outcome=outcome,  # type: ignore[arg-type]
        requested_action=action,
        hypothesis=hypothesis,
        state_transition=state_transition,
        evidence_level=evidence_level,  # type: ignore[arg-type]
        proof_status=proof_status,
        confidence=confidence,
        trust_level=trust_level,  # type: ignore[arg-type]
        impact_level=impact_level,  # type: ignore[arg-type]
        requires_confirmation=True,
        confirmation_phrase=EDGE_CONFIRMATION_PHRASE,
        reason_codes=list(dict.fromkeys(reason_codes)),
        blocked_actions=_edge_blocked_actions(outcome, action),
        limitations=limitations,
        recommended_next_steps=["Show remediation preview and require typed operator confirmation."],
    )

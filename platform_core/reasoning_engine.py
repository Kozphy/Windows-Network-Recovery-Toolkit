"""Deterministic event/state reasoning engine for endpoint reliability."""

from __future__ import annotations

from typing import Any

from platform_core.evidence_tree import build_evidence_tree
from platform_core.failure_scenarios import (
    default_failure_scenarios,
    detect_endpoint_events,
    event_types,
    normalize_signals,
)
from platform_core.impact_score import calculate_reliability_impact
from platform_core.reasoning_models import (
    EndpointEvent,
    EvidenceTree,
    Observation,
    PolicyDecision,
    ProofResult,
    ReasoningRun,
    StateTransition,
    new_id,
)

SAFE_REGISTRY_ACTIONS = {"restore_proxy", "disable_proxy", "reset_wininet_proxy", "restore_known_good_proxy"}
DESTRUCTIVE_ACTION_TOKENS = ("firewall", "adapter_disable", "kill", "process_kill", "arbitrary_shell", "netsh_reset")


def _has(signals: dict[str, Any], name: str) -> bool:
    """Return whether a normalized signal is true."""
    value = signals.get(name)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "ok", "success", "succeeded", "enabled", "1"}
    return bool(value)


def _event_ids_for(required: set[str], events: list[EndpointEvent]) -> list[str]:
    """Return event IDs matching required event types."""
    return [event.id for event in events if event.event_type in required]


def infer_browser_proxy_transitions(events: list[EndpointEvent], signals: dict[str, Any]) -> list[StateTransition]:
    """Infer state transitions for the browser proxy path scenario."""
    observed = event_types(events)
    transitions: list[StateTransition] = []
    current = "healthy_browser_path"

    drift_events = {"wininet_proxy_changed", "wininet_proxy_enabled", "localhost_proxy_detected"} & observed
    if drift_events:
        transitions.append(
            StateTransition(
                from_state=current,
                to_state="proxy_drift_detected",
                rule_id="proxy_drift",
                confidence=0.72,
                event_ids=_event_ids_for(drift_events, events),
            )
        )
        current = "proxy_drift_detected"

    suspect_required = {"ping_ok", "dns_ok", "tcp443_ok", "browser_https_failed", "wininet_proxy_enabled"}
    if suspect_required.issubset(observed):
        transitions.append(
            StateTransition(
                from_state=current,
                to_state="browser_path_failure_suspected",
                rule_id="browser_path_suspected",
                confidence=0.84,
                event_ids=_event_ids_for(suspect_required, events),
            )
        )
        current = "browser_path_failure_suspected"

    confirmed_required = {"proxy_bypass_succeeded", "proxied_path_failed"}
    if confirmed_required.issubset(observed):
        transitions.append(
            StateTransition(
                from_state=current,
                to_state="proxy_path_failure_confirmed",
                rule_id="proxy_path_confirmed",
                confidence=0.92,
                evidence_level="validated",
                event_ids=_event_ids_for(confirmed_required, events),
            )
        )
        current = "proxy_path_failure_confirmed"

    if _has(signals, "policy_preview_allowed") and current == "proxy_path_failure_confirmed":
        transitions.append(
            StateTransition(
                from_state=current,
                to_state="remediation_preview_ready",
                rule_id="preview_ready",
                confidence=0.90,
                evidence_level="validated",
                event_ids=_event_ids_for({"policy_preview_allowed"}, events),
            )
        )
    return transitions


def reject_alternatives(signals: dict[str, Any]) -> list[dict[str, str]]:
    """Return alternative hypotheses rejected by observed positive controls."""
    rejected: list[dict[str, str]] = []
    if _has(signals, "ping_ok") or _has(signals, "dns_ok") or _has(signals, "tcp443_ok"):
        rejected.append({"hypothesis": "total_network_outage", "reason": "ping/dns/tcp checks succeeded"})
    if _has(signals, "dns_ok"):
        rejected.append({"hypothesis": "dns_only_failure", "reason": "dns resolution succeeded"})
    if _has(signals, "tcp443_ok"):
        rejected.append({"hypothesis": "tcp_blocked", "reason": "TCP 443 connectivity succeeded"})
    if _has(signals, "tcp443_ok") and _has(signals, "proxy_bypass_succeeded"):
        rejected.append({"hypothesis": "upstream_isp_issue", "reason": "direct HTTPS path succeeded outside proxy"})
    if _has(signals, "proxy_bypass_succeeded") and not _has(signals, "tls_certificate_error"):
        rejected.append({"hypothesis": "certificate_tls_issue", "reason": "proxy bypass succeeded without TLS error signal"})
    return rejected


def rank_hypotheses(
    *,
    transitions: list[StateTransition],
    signals: dict[str, Any],
    proof_result: ProofResult,
) -> list[dict[str, Any]]:
    """Rank competing hypotheses from events, transitions, and proof status."""
    score = 0.20
    evidence: list[str] = []
    for name in ("ping_ok", "dns_ok", "tcp443_ok", "browser_https_failed", "wininet_proxy_enabled"):
        if _has(signals, name):
            score += 0.10
            evidence.append(name)
    if _has(signals, "localhost_proxy_detected"):
        score += 0.08
        evidence.append("localhost_proxy_detected")
    if _has(signals, "proxy_bypass_succeeded") and _has(signals, "proxied_path_failed"):
        score += 0.18
        evidence.extend(["proxy_bypass_succeeded", "proxied_path_failed"])
    if proof_result.status == "CONFIRMED":
        score += 0.12
        evidence.append("proof_confirmed")
    if not transitions:
        score = min(score, 0.30)

    score = round(max(0.0, min(0.98, score)), 2)
    alternatives = reject_alternatives(signals)
    ranking = [
        {
            "hypothesis": "browser_proxy_path_regression",
            "confidence": score,
            "evidence": evidence,
            "state_depth": len(transitions),
        }
    ]
    ranking.extend(
        {
            "hypothesis": item["hypothesis"],
            "confidence": 0.10,
            "evidence": [item["reason"]],
            "rejected": True,
        }
        for item in alternatives
    )
    return ranking


def evaluate_reasoning_policy(
    *,
    hypothesis: str,
    transitions: list[StateTransition],
    proof_result: ProofResult,
    confidence: float,
    impact_level: str,
    requested_action: str | None,
    explicit_confirmation: bool = False,
    conflicting_signals: bool = False,
) -> PolicyDecision:
    """Evaluate reasoning-aware policy without executing remediation.

    Args:
        hypothesis: Accepted hypothesis ID.
        transitions: State transitions for the run.
        proof_result: Optional proof result.
        confidence: Ordinal hypothesis confidence.
        impact_level: Reliability impact level.
        requested_action: Optional remediation action key.
        explicit_confirmation: Whether a typed confirmation boundary was met.
        conflicting_signals: Whether observations contain direct contradictions.

    Returns:
        Policy decision. The function never performs remediation.
    """
    action = (requested_action or "").strip().lower() or None
    reason_codes: list[str] = []
    limitations: list[str] = []
    state_transition = transitions[-1].to_state if transitions else "unknown"
    evidence_level = "proof" if proof_result.status == "CONFIRMED" else ("validated" if transitions else "inferred")
    trust_level = "low" if conflicting_signals else ("high" if proof_result.status == "CONFIRMED" else "medium")

    if action and any(token in action for token in DESTRUCTIVE_ACTION_TOKENS):
        return PolicyDecision(
            outcome="BLOCK",
            requested_action=action,
            hypothesis=hypothesis,
            state_transition=state_transition,
            evidence_level=evidence_level,  # type: ignore[arg-type]
            proof_status=proof_result.status,
            confidence=confidence,
            trust_level=trust_level,  # type: ignore[arg-type]
            impact_level=impact_level,  # type: ignore[arg-type]
            reason_codes=["destructive_or_manual_only_action_blocked"],
            limitations=["Firewall reset, adapter disable, process kill, and arbitrary shell remain blocked."],
            recommended_next_steps=["Use manual incident response after preserving evidence."],
        )

    if not action:
        return PolicyDecision(
            outcome="PREVIEW",
            requested_action=None,
            hypothesis=hypothesis,
            state_transition=state_transition,
            evidence_level=evidence_level,  # type: ignore[arg-type]
            proof_status=proof_result.status,
            confidence=confidence,
            trust_level=trust_level,  # type: ignore[arg-type]
            impact_level=impact_level,  # type: ignore[arg-type]
            reason_codes=["diagnostic_only_no_remediation_requested"],
            recommended_next_steps=["Run preview with a safe remediation action if repair is needed."],
        )

    if action not in SAFE_REGISTRY_ACTIONS:
        return PolicyDecision(
            outcome="BLOCK",
            requested_action=action,
            hypothesis=hypothesis,
            state_transition=state_transition,
            evidence_level=evidence_level,  # type: ignore[arg-type]
            proof_status=proof_result.status,
            confidence=confidence,
            trust_level=trust_level,  # type: ignore[arg-type]
            impact_level=impact_level,  # type: ignore[arg-type]
            reason_codes=["unknown_or_unallowlisted_action"],
            limitations=["Only allowlisted remediation action keys can pass policy."],
            recommended_next_steps=["Choose an allowlisted preview action or continue diagnostics."],
        )

    if conflicting_signals:
        reason_codes.append("conflicting_signals_downgrade_to_preview")
        limitations.append("Conflicting observations reduce trust; live execution is not allowed.")
        outcome = "PREVIEW"
    elif proof_result.status == "CONFIRMED" and explicit_confirmation:
        reason_codes.append("confirmed_proof_safe_action_confirmation_present")
        outcome = "ALLOW"
    else:
        reason_codes.append("preview_required_until_proof_and_confirmation")
        outcome = "PREVIEW"

    if impact_level in ("high", "critical") and proof_result.status != "CONFIRMED":
        reason_codes.append("high_impact_requires_confirmed_proof_before_execute")
    if impact_level == "critical" and trust_level != "high":
        reason_codes.append("critical_impact_requires_high_trust_for_execute_authority")

    if proof_result.status != "CONFIRMED":
        reason_codes.append("unproven_high_confidence_is_not_execute_authority")
    if action in SAFE_REGISTRY_ACTIONS:
        reason_codes.append("registry_change_requires_typed_confirmation")

    return PolicyDecision(
        outcome=outcome,  # type: ignore[arg-type]
        requested_action=action,
        hypothesis=hypothesis,
        state_transition=state_transition,
        evidence_level=evidence_level,  # type: ignore[arg-type]
        proof_status=proof_result.status,
        confidence=confidence,
        trust_level=trust_level,  # type: ignore[arg-type]
        impact_level=impact_level,  # type: ignore[arg-type]
        requires_confirmation=action in SAFE_REGISTRY_ACTIONS,
        confirmation_phrase="RESTORE_PROXY" if action in SAFE_REGISTRY_ACTIONS else None,
        reason_codes=list(dict.fromkeys(reason_codes)),
        limitations=limitations,
        recommended_next_steps=["Show remediation preview and require typed operator confirmation."],
    )


def _conflicting_signals(signals: dict[str, Any]) -> bool:
    """Return whether directly contradictory signals are present."""
    return (_has(signals, "browser_https_failed") and _has(signals, "browser_https_ok")) or (
        _has(signals, "dns_ok") and _has(signals, "dns_failed")
    )


def run_reasoning(
    observations: list[Observation],
    *,
    proof_result: ProofResult | None = None,
    requested_action: str | None = None,
    explicit_confirmation: bool = False,
    source: str = "reasoning_engine",
    run_id: str | None = None,
) -> ReasoningRun:
    """Run the deterministic endpoint reasoning pipeline.

    Args:
        observations: Replayable observations. No machine probes happen here.
        proof_result: Optional proof result from a targeted checker.
        requested_action: Optional remediation action key for policy evaluation.
        explicit_confirmation: Whether typed confirmation boundary was met.
        source: Caller source.
        run_id: Optional stable ID for replay parity.

    Returns:
        Full reasoning run with events, transitions, evidence tree, policy, and impact.
    """
    scenarios = default_failure_scenarios()
    proof = proof_result or ProofResult(hypothesis="browser_proxy_path_regression")
    rid = run_id or new_id("run")
    signals = normalize_signals(observations)
    events = detect_endpoint_events(observations)
    transitions = infer_browser_proxy_transitions(events, signals)
    ranking = rank_hypotheses(transitions=transitions, signals=signals, proof_result=proof)
    accepted = ranking[0]["hypothesis"] if ranking else "unknown"
    confidence = float(ranking[0]["confidence"]) if ranking else 0.0
    rejected = reject_alternatives(signals)
    scenario = scenarios["browser_proxy_path_regression"]
    limitations = list(scenario.limitations)
    if _conflicting_signals(signals):
        limitations.append("Conflicting signals were observed; policy is downgraded to preview.")
    if proof.status == "NOT_RUN":
        limitations.append("Proof checks were not run; confidence remains heuristic.")

    severity = "high" if _has(signals, "browser_https_failed") else "medium"
    scope = "browser_and_dev_tools" if _has(signals, "proxied_path_failed") else "browser_only"
    impact = calculate_reliability_impact(
        severity=severity,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        confidence=confidence,
        duration_factor="unknown",
    )
    policy = evaluate_reasoning_policy(
        hypothesis=accepted,
        transitions=transitions,
        proof_result=proof,
        confidence=confidence,
        impact_level=impact.impact_level,
        requested_action=requested_action,
        explicit_confirmation=explicit_confirmation,
        conflicting_signals=_conflicting_signals(signals),
    )
    if policy.outcome == "PREVIEW":
        preview = {
            "action": requested_action,
            "dry_run": True,
            "requires_confirmation": policy.requires_confirmation,
            "confirmation_phrase": policy.confirmation_phrase,
        }
    else:
        preview = {}
    recommendations = list(dict.fromkeys(scenario.recommended_next_steps + policy.recommended_next_steps))
    tree: EvidenceTree = build_evidence_tree(
        run_id=rid,
        accepted_hypothesis=accepted,
        events=events,
        transitions=transitions,
        rejected_alternatives=rejected,
        proof_result=proof,
        limitations=limitations + policy.limitations,
        recommended_next_steps=recommendations,
    )
    return ReasoningRun(
        id=rid,
        source=source,
        raw_observations=observations,
        normalized_signals=signals,
        detected_events=events,
        state_transitions=transitions,
        hypothesis_ranking=ranking,
        accepted_hypothesis=accepted,
        evidence_tree=tree,
        proof_result=proof,
        reliability_impact=impact,
        policy_decision=policy,
        recommended_next_test="Run proxy bypass contrast proof if not already confirmed.",
        remediation_preview=preview,
        limitations=list(dict.fromkeys(limitations + proof.limitations + policy.limitations)),
        recommended_next_steps=recommendations,
    )


def observation(name: str, value: Any = True, *, source: str = "fixture", confidence: float = 1.0) -> Observation:
    """Convenience constructor for tests and fixtures."""
    return Observation(source=source, signal_name=name, value=value, normalized_value=value, confidence=confidence)

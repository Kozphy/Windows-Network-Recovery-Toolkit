"""Deterministic edge-device reasoning engine (observation -> ... -> policy).

Module responsibility:
    Orchestrate the full edge reasoning chain that mirrors the platform engine's style:
    observation -> event -> state transition -> ranked hypotheses -> evidence tree ->
    optional proof -> impact score -> policy -> (caller persists audit).

System placement:
    Pure compute layer used by :mod:`edge_device.cli_handlers`. No hardware access, no
    subprocess, no I/O — replayable from stored observations.

Key invariants:
    * Pure with respect to inputs: identical observations + proof + requested_action +
      confirmation always yield the same policy outcome and reason codes (only auto-generated
      ids differ).
    * Only cataloged hypotheses (see :mod:`edge_device.scenarios`) are ever accepted; no
      fabricated root cause is emitted.
    * Confidence and impact are ordinal — never calibrated probabilities.

Output guarantees:
    Returns an :class:`~edge_device.models.EdgeReasoningRun` that is JSON-serializable and
    carries explicitly separated supporting / contradicting / missing evidence.

Side effects:
    None. Persistence is the caller's responsibility (:mod:`edge_device.audit`).
"""

from __future__ import annotations

from typing import Any

from platform_core.reasoning_models import (
    EndpointEvent,
    EvidenceNode,
    EvidenceTree,
    Observation,
    ProofResult,
    StateTransition,
    new_id,
)
from edge_device.models import EdgeImpact, EdgeReasoningRun
from edge_device.policy import EDGE_SAFE_ACTIONS, evaluate_edge_policy
from edge_device.scenarios import (
    NOMINAL_HYPOTHESIS,
    conflicting_edge_signals,
    rank_edge_hypotheses,
    scenario_by_id,
)
from edge_device.signals import detect_edge_events, normalize_edge_signals, observations_from_raw

_LIMITATIONS = (
    "Edge signals are simulated; no real FPGA/NPU/x86-embedded hardware is queried.",
    "Confidence and impact are ordinal rankings, not calibrated probabilities.",
    "Listener/process/heuristic context never proves a hardware-fault root cause without "
    "vendor telemetry; proof checks here are simulated contrasts.",
)


def _state_path(signals: dict[str, Any]) -> list[str]:
    """Derive an ordered edge runtime state path from canonical signals."""
    path = ["EDGE_BASELINE"]
    if signals.get("npu_available") and not signals.get("npu_unavailable"):
        path.append("NPU_INFERENCE_ACTIVE")
    if signals.get("npu_unavailable"):
        path.append("CPU_FALLBACK_INFERENCE")
    if signals.get("driver_mismatch"):
        path.append("DRIVER_RUNTIME_MISMATCH")
    if signals.get("thermal_warn") or signals.get("thermal_hot"):
        path.append("THERMAL_THROTTLING_RISK")
    if signals.get("latency_regression") or signals.get("inference_error_high"):
        path.append("INFERENCE_DEGRADED")
    if signals.get("sensor_degraded"):
        path.append("SENSOR_DEGRADED")
    if signals.get("uplink_degraded") and signals.get("local_inference_ok"):
        path.append("UPLINK_DEGRADED_LOCAL_OK")
    if len(path) == 1:
        path.append("EDGE_HEALTHY")
    return path


def _build_transitions(events: list[EndpointEvent], state_path: list[str]) -> list[StateTransition]:
    """Build ordered state transitions linking consecutive states in the path."""
    event_ids = [e.id for e in events]
    transitions: list[StateTransition] = []
    for frm, to in zip(state_path, state_path[1:]):
        transitions.append(
            StateTransition(
                source="edge_reasoning",
                from_state=frm,
                to_state=to,
                event_ids=event_ids,
                rule_id="edge_state_machine",
                evidence_level="inferred",
            )
        )
    return transitions


def _impact_for(hypothesis: str, signals: dict[str, Any], confidence: float) -> EdgeImpact:
    """Derive a deterministic edge impact from the accepted hypothesis and signals."""
    if hypothesis == "uplink_degraded_but_local_inference_ok":
        return EdgeImpact(
            severity="low",
            scope="device_and_uplink",
            impact_score=round(min(0.4, 0.2 + 0.1 * confidence), 4),
            impact_level="low",
            explanation="Uplink degraded but local inference remains healthy; cloud sync delayed only.",
        )
    if hypothesis == NOMINAL_HYPOTHESIS or hypothesis == "edge_state_indeterminate":
        return EdgeImpact(
            severity="low",
            scope="none",
            impact_score=0.05,
            impact_level="low",
            explanation="No cataloged failure pattern matched; device appears nominal.",
        )

    severe = bool(
        signals.get("thermal_hot")
        or signals.get("driver_mismatch")
        or signals.get("inference_error_high")
        or signals.get("sensor_lost")
    )
    moderate = bool(
        signals.get("thermal_warn")
        or signals.get("latency_regression")
        or signals.get("npu_unavailable")
        or signals.get("sensor_degraded")
    )
    if severe:
        severity = "high"
        score = 0.75
    elif moderate:
        severity = "medium"
        score = 0.55
    else:
        severity = "low"
        score = 0.3
    return EdgeImpact(
        severity=severity,  # type: ignore[arg-type]
        scope="device_local",
        impact_score=round(min(0.95, score + 0.05 * confidence), 4),
        impact_level=severity,  # type: ignore[arg-type]
        explanation=f"Accepted hypothesis '{hypothesis}' implies {severity} local inference reliability impact.",
    )


def _build_evidence_tree(
    *,
    run_id: str,
    accepted: str,
    state_path: list[str],
    supporting: list[str],
    contradicting: list[str],
    missing: list[str],
    rejected: list[dict[str, str]],
) -> EvidenceTree:
    """Assemble an explainable evidence tree for the accepted hypothesis."""
    children = [
        EvidenceNode(
            source="edge_reasoning",
            label="supporting_evidence",
            evidence_level="inferred",
            details={"signals": supporting},
        ),
        EvidenceNode(
            source="edge_reasoning",
            label="contradicting_evidence",
            evidence_level="inferred",
            details={"signals": contradicting},
        ),
        EvidenceNode(
            source="edge_reasoning",
            label="missing_evidence",
            evidence_level="inferred",
            details={"signals": missing},
        ),
    ]
    root = EvidenceNode(
        source="edge_reasoning",
        label=f"accepted:{accepted}",
        evidence_level="inferred",
        details={"state_path": state_path},
        children=children,
    )
    return EvidenceTree(
        source="edge_reasoning",
        run_id=run_id,
        accepted_hypothesis=accepted,
        state_path=state_path,
        accepted_because=supporting,
        rejected_alternatives=rejected,
        root=root,
        limitations=list(_LIMITATIONS),
    )


def run_edge_reasoning(
    raw_observations: dict[str, Any],
    *,
    device_profile: dict[str, Any] | None = None,
    proof_result: ProofResult | None = None,
    requested_action: str | None = None,
    explicit_confirmation: bool = False,
    source: str = "edge_reasoning",
    run_id: str | None = None,
) -> EdgeReasoningRun:
    """Drive the deterministic edge Observation -> Decision pipeline.

    Args:
        raw_observations: Flat device telemetry mapping (cpu_load, temperature_celsius,
            npu_available, inference_latency_ms, inference_error_rate, driver_status,
            sensor_input_status, network_uplink_status, ...).
        device_profile: Optional descriptive metadata (device_id, class, model). Never used
            for scoring; persisted for audit context.
        proof_result: Optional simulated proof outcome. ``CONFIRMED`` is required (with
            explicit confirmation, no conflicts, non-critical impact) for an ALLOW outcome.
        requested_action: Optional remediation key. ``None`` -> diagnostic-only PREVIEW.
        explicit_confirmation: ``True`` when the operator typed the confirmation phrase.
        source: Provenance label persisted on the run.
        run_id: Optional stable id for replay parity; generated when omitted.

    Returns:
        :class:`~edge_device.models.EdgeReasoningRun` with the full reasoning chain.

    Side effects:
        None. Use :mod:`edge_device.audit` to persist the returned run.
    """
    rid = run_id or new_id("edge_run")
    proof = proof_result or ProofResult(source="edge_proof_engine")
    observations: list[Observation] = observations_from_raw(raw_observations)
    signals = normalize_edge_signals(raw_observations)
    events = detect_edge_events(signals, observations)
    state_path = _state_path(signals)
    transitions = _build_transitions(events, state_path)

    proof_confirmed = proof.status == "CONFIRMED"
    ranking = rank_edge_hypotheses(
        signals,
        proof_hypothesis=proof.hypothesis,
        proof_confirmed=proof_confirmed,
    )
    accepted_row = ranking[0]
    accepted = str(accepted_row["hypothesis"])
    confidence = float(accepted_row["confidence"])
    supporting = list(accepted_row.get("supporting") or [])
    contradicting = list(accepted_row.get("contradicting") or [])
    missing = list(accepted_row.get("missing") or [])

    rejected = [
        {"hypothesis": str(r["hypothesis"]), "reason": "lower_ordinal_confidence"}
        for r in ranking[1:]
    ]

    impact = _impact_for(accepted, signals, confidence)
    conflicts = conflicting_edge_signals(signals)
    state_transition = state_path[-1] if state_path else "unknown"

    policy = evaluate_edge_policy(
        hypothesis=accepted,
        state_transition=state_transition,
        proof_result=proof,
        confidence=confidence,
        impact_level=impact.impact_level,
        requested_action=requested_action,
        explicit_confirmation=explicit_confirmation,
        conflicting_signals=conflicts,
    )

    scenario = scenario_by_id(accepted)
    safe_next_action = scenario.safe_action if scenario else None
    recommended_next_test = scenario.proof_check if scenario else ""

    evidence_tree = _build_evidence_tree(
        run_id=rid,
        accepted=accepted,
        state_path=state_path,
        supporting=supporting,
        contradicting=contradicting,
        missing=missing,
        rejected=rejected,
    )

    next_steps: list[str] = []
    if policy.outcome == "PREVIEW" and safe_next_action and policy.requested_action is None:
        next_steps.append(f"Preview safe action '{safe_next_action}' if intervention is needed.")
    if recommended_next_test:
        next_steps.append(f"Run proof check '{recommended_next_test}' to strengthen or reject the hypothesis.")

    return EdgeReasoningRun(
        id=rid,
        source=source,
        device_profile=device_profile or {},
        raw_observations=observations,
        normalized_signals=signals,
        detected_events=events,
        state_transitions=transitions,
        hypothesis_ranking=ranking,
        accepted_hypothesis=accepted,
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        missing_evidence=missing,
        evidence_tree=evidence_tree,
        proof_result=proof,
        reliability_impact=impact,
        policy_decision=policy,
        safe_next_action=safe_next_action,
        recommended_next_test=recommended_next_test,
        limitations=list(_LIMITATIONS),
        recommended_next_steps=next_steps,
    )


def is_safe_edge_action(action: str | None) -> bool:
    """Return whether ``action`` is an allowlisted low-risk edge action."""
    return (action or "").strip().lower() in EDGE_SAFE_ACTIONS

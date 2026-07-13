"""Typed models for the simulated AI-edge / embedded-compute reliability layer.

Module responsibility:
    Define edge-specific impact and the full :class:`EdgeReasoningRun` envelope. Reuses the
    platform reasoning primitives (:class:`Observation`, :class:`EndpointEvent`,
    :class:`StateTransition`, :class:`EvidenceTree`, :class:`ProofResult`,
    :class:`PolicyDecision`) so JSON shape, replay, and audit conventions stay consistent
    with the existing endpoint reliability engine.

System placement:
    Output type of :mod:`edge_device.reasoning`; serialized to ``logs/edge_runs.jsonl`` by
    :mod:`edge_device.audit` and rendered by :mod:`edge_device.cli_handlers`.

Key invariants:
    * ``confidence`` and ``impact_score`` are ordinal in ``[0.0, 1.0]`` — not calibrated
      probabilities.
    * ``EdgeImpact.scope`` uses an edge-specific vocabulary (distinct from the proxy/browser
      ``ImpactScope``) to avoid overstating blast radius.

Output guarantees:
    :meth:`EdgeReasoningRun.to_output_dict` returns the operator/JSON contract with the
    explicitly separated evidence sections required by the CLI.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from platform_core.models import utc_now_iso
from platform_core.reasoning_models import (
    AuditMetadata,
    EndpointEvent,
    EvidenceTree,
    ImpactSeverity,
    Observation,
    PolicyDecision,
    ProofResult,
    StateTransition,
    new_id,
)

EdgeImpactScope = Literal["inference_only", "device_local", "device_and_uplink", "fleet", "none"]


class EdgeImpact(BaseModel):
    """Explainable reliability impact for an edge-device reasoning run.

    Attributes:
        severity: Ordinal severity bucket.
        scope: Edge-specific blast radius (inference-only, device-local, device+uplink, fleet).
        impact_score: Ordinal score in ``[0.0, 1.0]`` (not a probability).
        impact_level: Final bucket used by the policy gate.
        explanation: Short human-readable rationale derived from signals only.
    """

    id: str = Field(default_factory=lambda: new_id("edge_impact"))
    timestamp: str = Field(default_factory=utc_now_iso)
    source: str = "edge_impact"
    severity: ImpactSeverity = "low"
    scope: EdgeImpactScope = "none"
    impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    impact_level: ImpactSeverity = "low"
    explanation: str = ""
    limitations: list[str] = Field(default_factory=list)
    audit_metadata: AuditMetadata = Field(default_factory=lambda: AuditMetadata(schema_version="edge.v1"))


class EdgeReasoningRun(BaseModel):
    """Full replayable edge reasoning run (observation -> ... -> policy -> audit)."""

    id: str = Field(default_factory=lambda: new_id("edge_run"))
    timestamp: str = Field(default_factory=utc_now_iso)
    source: str = "edge_reasoning"
    schema_version: str = "edge.v1"
    device_profile: dict[str, Any] = Field(default_factory=dict)
    raw_observations: list[Observation] = Field(default_factory=list)
    normalized_signals: dict[str, Any] = Field(default_factory=dict)
    detected_events: list[EndpointEvent] = Field(default_factory=list)
    state_transitions: list[StateTransition] = Field(default_factory=list)
    hypothesis_ranking: list[dict[str, Any]] = Field(default_factory=list)
    accepted_hypothesis: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence_tree: EvidenceTree
    proof_result: ProofResult = Field(default_factory=ProofResult)
    reliability_impact: EdgeImpact
    policy_decision: PolicyDecision
    safe_next_action: str | None = None
    recommended_next_test: str = ""
    limitations: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    audit_metadata: AuditMetadata = Field(default_factory=lambda: AuditMetadata(schema_version="edge.v1"))
    version_metadata: dict[str, str] = Field(
        default_factory=lambda: {"edge_schema": "edge.v1", "engine_version": "2026.05"}
    )

    def to_output_dict(self) -> dict[str, Any]:
        """Return the operator/JSON contract with explicitly separated evidence sections.

        Returns:
            Dict with ``observed_signals``, ``inferred_hypotheses``, ``supporting_evidence``,
            ``contradicting_evidence``, ``missing_evidence``, ``proof_status``,
            ``policy_decision``, ``safe_next_action``, ``blocked_actions``, plus the full
            reasoning chain (events, transitions, evidence tree, impact) for replay/audit.
        """
        policy = self.policy_decision
        return {
            "schema_version": self.schema_version,
            "run_id": self.id,
            "timestamp": self.timestamp,
            "device_profile": self.device_profile,
            "observed_signals": self.normalized_signals,
            "inferred_hypotheses": [
                {"hypothesis": r["hypothesis"], "title": r.get("title", ""), "confidence": r["confidence"]}
                for r in self.hypothesis_ranking
            ],
            "accepted_hypothesis": self.accepted_hypothesis,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "missing_evidence": self.missing_evidence,
            "proof_status": self.proof_result.status,
            "policy_decision": {
                "decision": policy.outcome,
                "requested_action": policy.requested_action,
                "reason_codes": policy.reason_codes,
                "trust_level": policy.trust_level,
                "impact_level": policy.impact_level,
                "requires_confirmation": policy.requires_confirmation,
                "confirmation_phrase": policy.confirmation_phrase,
            },
            "safe_next_action": self.safe_next_action,
            "blocked_actions": policy.blocked_actions,
            "reliability_impact": {
                "severity": self.reliability_impact.severity,
                "scope": self.reliability_impact.scope,
                "impact_level": self.reliability_impact.impact_level,
                "impact_score": self.reliability_impact.impact_score,
                "explanation": self.reliability_impact.explanation,
            },
            "events": [e.model_dump(mode="json") for e in self.detected_events],
            "state_transitions": [t.model_dump(mode="json") for t in self.state_transitions],
            "evidence_tree": self.evidence_tree.model_dump(mode="json"),
            "recommended_next_test": self.recommended_next_test,
            "limitations": self.limitations,
            "recommended_next_steps": self.recommended_next_steps,
            "replay_mode": "deterministic_no_hardware",
        }

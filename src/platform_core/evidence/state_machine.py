"""Formal evidence tier state machine."""

from __future__ import annotations

from typing import Any

from .guards import ProofInputs, proof_inputs_from_signals, validate_tier_upgrade
from .tiers import EvidenceTier, normalize_tier


class EvidenceStateMachine:
    """Stateful tier tracker with guarded transitions only."""

    def __init__(self, initial: EvidenceTier = "OBSERVED_ONLY") -> None:
        self.tier: EvidenceTier = initial

    def propose(self, proposed: EvidenceTier, proof: ProofInputs) -> tuple[bool, str]:
        allowed, reason = validate_tier_upgrade(self.tier, proposed, proof)
        if allowed and proposed != self.tier:
            self.tier = proposed
        return allowed, reason

    def apply_signals(self, signals: dict[str, Any]) -> EvidenceTier:
        proof = proof_inputs_from_signals(signals)
        # Deterministic upgrade path from signals
        candidates: list[EvidenceTier] = ["OBSERVED_ONLY"]
        if proof.has_listener_correlation_only or any(
            k in signals for k in ("listener_on_proxy_port", "listener_process_name")
        ):
            candidates.append("CORRELATED")
        if proof.has_path_validation:
            candidates.append("PROVEN_NETWORK_IMPACT")
        if proof.has_registry_writer_telemetry:
            candidates.append("PROVEN_REGISTRY_WRITER")
        if proof.has_registry_writer_telemetry and proof.has_path_validation:
            if proof.has_process_lineage and proof.has_timestamp_alignment:
                candidates.append("FINAL_CAUSATION")

        for tier in candidates:
            self.propose(tier, proof)
        return self.tier

    @classmethod
    def from_legacy_level(cls, level: str) -> EvidenceStateMachine:
        return cls(initial=normalize_tier(level))

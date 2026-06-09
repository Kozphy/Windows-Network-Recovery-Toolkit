"""Evidence tier upgrade guards — Observation != Proof."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tiers import EvidenceTier, tier_rank


@dataclass(frozen=True)
class ProofInputs:
    has_registry_writer_telemetry: bool = False
    has_process_lineage: bool = False
    has_timestamp_alignment: bool = False
    has_path_validation: bool = False
    has_listener_correlation_only: bool = False
    has_replay_certification: bool = False
    manual_tier_override: bool = False  # must always be False from API/CLI


def validate_tier_upgrade(
    current: EvidenceTier,
    proposed: EvidenceTier,
    proof: ProofInputs,
) -> tuple[bool, str]:
    """Return (allowed, reason). Manual FINAL_CAUSATION override is always rejected."""
    if proof.manual_tier_override and proposed == "FINAL_CAUSATION":
        return False, "Manual FINAL_CAUSATION override forbidden"

    if tier_rank(proposed) <= tier_rank(current):
        return proposed == current, "No downgrade" if proposed != current else "unchanged"

    if proposed == "CORRELATED":
        return proof.has_listener_correlation_only or True, "correlation observed"

    if proposed == "PROVEN_NETWORK_IMPACT":
        return proof.has_path_validation, "PROVEN_NETWORK_IMPACT requires network path validation proof"

    if proposed == "PROVEN_REGISTRY_WRITER":
        return proof.has_registry_writer_telemetry, "PROVEN_REGISTRY_WRITER requires writer telemetry"

    if proposed == "FINAL_CAUSATION":
        ok = (
            proof.has_registry_writer_telemetry
            and proof.has_process_lineage
            and proof.has_timestamp_alignment
            and proof.has_path_validation
        )
        if not ok:
            return False, "FINAL_CAUSATION requires writer + lineage + alignment + path validation"
        return True, "guarded proof satisfied"

    return False, f"Unknown tier transition to {proposed}"


def can_unlock_destructive_remediation(tier: EvidenceTier, proof: ProofInputs) -> bool:
    """Correlation-only evidence must never unlock destructive remediation."""
    if proof.has_listener_correlation_only and not proof.has_registry_writer_telemetry:
        return False
    if tier_rank(tier) < tier_rank("FINAL_CAUSATION"):
        return False
    allowed, _ = validate_tier_upgrade("PROVEN_REGISTRY_WRITER", "FINAL_CAUSATION", proof)
    return allowed


def proof_inputs_from_signals(signals: dict[str, Any]) -> ProofInputs:
    def truthy(v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return bool(v)

    return ProofInputs(
        has_registry_writer_telemetry=truthy(
            signals.get("sysmon_event_13") or signals.get("registry_writer_observed")
        ),
        has_process_lineage=truthy(signals.get("writer_process") or signals.get("process_lineage")),
        has_timestamp_alignment=truthy(signals.get("timestamp_alignment")),
        has_path_validation=truthy(
            signals.get("proxy_bypass_succeeded")
            or signals.get("direct_path_success")
            or signals.get("path_validated")
        ),
        has_listener_correlation_only=truthy(
            signals.get("listener_on_proxy_port") or signals.get("listener_correlation")
        )
        and not truthy(signals.get("sysmon_event_13")),
        has_replay_certification=truthy(signals.get("replay_certified")),
        manual_tier_override=truthy(signals.get("force_final_causation")),
    )

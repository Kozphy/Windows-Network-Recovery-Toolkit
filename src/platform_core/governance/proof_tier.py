"""Formal proof-tier taxonomy for technology risk decisions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProofTier(StrEnum):
    T0_OBSERVATION_ONLY = "T0_OBSERVATION_ONLY"
    T1_LOCAL_CONFIG_EVIDENCE = "T1_LOCAL_CONFIG_EVIDENCE"
    T2_RUNTIME_CORROBORATION = "T2_RUNTIME_CORROBORATION"
    T3_BEHAVIORAL_REPRODUCTION = "T3_BEHAVIORAL_REPRODUCTION"
    T4_OPERATOR_CONFIRMED = "T4_OPERATOR_CONFIRMED"


_TIER_ORDER = [
    ProofTier.T0_OBSERVATION_ONLY,
    ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
    ProofTier.T2_RUNTIME_CORROBORATION,
    ProofTier.T3_BEHAVIORAL_REPRODUCTION,
    ProofTier.T4_OPERATOR_CONFIRMED,
]

_DEFAULT_LIMITATIONS = [
    "Proof tiers describe evidence strength — not malware, compromise, or MITM confirmation.",
    "Observation is not proof; correlation is not causation.",
]


class ProofTierResult(BaseModel):
    proof_tier: ProofTier
    proof_tier_label: str
    confidence_cap: str = "ordinal_not_probability"
    limitations: list[str] = Field(default_factory=lambda: list(_DEFAULT_LIMITATIONS))
    rationale: str = ""


def _classification(fixture: dict[str, Any]) -> str:
    block = fixture.get("classification") or {}
    return str(block.get("primary_classification") or fixture.get("classification") or "").upper()


def _listener_found(fixture: dict[str, Any]) -> bool | None:
    owner = fixture.get("proxy_owner") or fixture.get("listener_info") or {}
    if "listener_found" in owner:
        return bool(owner.get("listener_found"))
    proxy_state = fixture.get("proxy_state") or fixture.get("proxy_status") or {}
    port = proxy_state.get("localhost_port")
    if port is not None and owner.get("process"):
        return True
    return None


def _proof_supported(fixture: dict[str, Any]) -> bool:
    proof = fixture.get("proof") or {}
    conclusion = proof.get("conclusion") or {}
    if conclusion.get("status") == "supported":
        return True
    for attempt in proof.get("proof_attempts") or []:
        if attempt.get("status") == "supported":
            return True
    return False


def _runtime_corroboration(fixture: dict[str, Any]) -> bool:
    proof = fixture.get("proof") or {}
    for attempt in proof.get("proof_attempts") or []:
        name = str(attempt.get("name", "")).lower()
        if name in {"localhost_listener_check", "wininet_winhttp_comparison", "direct_https_probe", "proxied_https_probe"}:
            if attempt.get("status") in ("supported", "failed"):
                return True
    return _proof_supported(fixture)


def _operator_confirmed(fixture: dict[str, Any]) -> bool:
    policy = fixture.get("policy_decision") or {}
    if policy.get("executed") and not policy.get("dry_run", True):
        return True
    if str(policy.get("confirmation_token_used") or "").strip():
        return True
    for row in fixture.get("audit_log_entries") or []:
        if row.get("confirmation_used") or row.get("executed"):
            return True
    return False


def resolve_proof_tier(fixture: dict[str, Any]) -> ProofTierResult:
    """Map fixture evidence to proof tier with conservative caps."""
    primary = _classification(fixture)
    listener = _listener_found(fixture)
    limitations = list(_DEFAULT_LIMITATIONS)
    rationale_parts: list[str] = []

    if _operator_confirmed(fixture):
        return ProofTierResult(
            proof_tier=ProofTier.T4_OPERATOR_CONFIRMED,
            proof_tier_label="Operator-confirmed action recorded",
            rationale="Human confirmation or executed remediation with audit evidence.",
            limitations=limitations + ["Operator confirmation does not prove absence of compromise."],
        )

    tier = ProofTier.T0_OBSERVATION_ONLY
    rationale_parts.append("Baseline observation from available signals.")

    if primary or fixture.get("proxy_state") or fixture.get("proxy_status"):
        tier = ProofTier.T1_LOCAL_CONFIG_EVIDENCE
        rationale_parts.append("Local WinINET/WinHTTP configuration evidence present.")

    if _runtime_corroboration(fixture):
        tier = ProofTier.T2_RUNTIME_CORROBORATION
        rationale_parts.append("Runtime path or stack contrast corroborates configuration hypothesis.")

    if primary == "DEAD_PROXY_CONFIG" and listener is False:
        tier = ProofTier.T1_LOCAL_CONFIG_EVIDENCE
        if _runtime_corroboration(fixture):
            tier = ProofTier.T2_RUNTIME_CORROBORATION
        else:
            rationale_parts.append(
                "Dead proxy without listener capped at T1–T2; no behavioral reproduction claimed."
            )
        limitations.append("Dead localhost proxy config does not imply malware or MITM.")

    if _proof_supported(fixture) and primary not in ("POSSIBLE_MITM_RISK",):
        if tier == ProofTier.T2_RUNTIME_CORROBORATION and primary != "DEAD_PROXY_CONFIG":
            tier = ProofTier.T3_BEHAVIORAL_REPRODUCTION
            rationale_parts.append("Structured proof checks support reproducible failure pattern.")
        elif primary == "DEAD_PROXY_CONFIG" and _runtime_corroboration(fixture):
            tier = ProofTier.T2_RUNTIME_CORROBORATION

    if primary in ("POSSIBLE_MITM_RISK", "SUSPICIOUS_PROXY"):
        cap = ProofTier.T2_RUNTIME_CORROBORATION
        if _TIER_ORDER.index(tier) > _TIER_ORDER.index(cap):
            tier = cap
        limitations.append("MITM or suspicious labels remain triage — not confirmed interception.")

    return ProofTierResult(
        proof_tier=tier,
        proof_tier_label=tier.value.replace("_", " ").title(),
        rationale=" ".join(rationale_parts),
        limitations=limitations,
    )

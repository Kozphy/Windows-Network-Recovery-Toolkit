"""B3 — full platform baseline.

Uses canonical Evidence → Aggregation → Proof Tier → Classification →
Control Tests → Policy Gate → Audit path from production-shaped code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from experiments.baselines.b1_flat_rules import predict_b1
from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1
from src.platform_core.governance.proof_tier import ProofTier, resolve_proof_tier
from windows_network_toolkit.analytics_pipeline import normalize_events_from_fixture
from windows_network_toolkit.incident_classifier import classify_incident_from_events

_UNSAFE_PHRASES = (
    "malware confirmed",
    "mitm confirmed",
    "compromised",
    "autonomous repair",
    "kill the process",
    "reset the firewall",
    "audit opinion",
    "safe to disable automatically",
)

_TIER_ORDER = [
    ProofTier.T0_OBSERVATION_ONLY,
    ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
    ProofTier.T2_RUNTIME_CORROBORATION,
    ProofTier.T3_BEHAVIORAL_REPRODUCTION,
    ProofTier.T4_OPERATOR_CONFIRMED,
    ProofTier.T5_GOVERNANCE_PROOF,
]


@dataclass
class AblationConfig:
    """Experiment-only ablation flags (A1–A7)."""

    remove_proof_tiers: bool = False  # A1
    remove_listener_process: bool = False  # A2
    remove_tls_path: bool = False  # A3
    remove_limitations: bool = False  # A4
    remove_policy_gate: bool = False  # A5
    remove_hash_chain: bool = False  # A6
    remove_cross_signal_aggregation: bool = False  # A7


def _normalize_policy(action: str, fixture: dict[str, Any]) -> str:
    token = action.strip().lower()
    if token in {"human_review", "investigate_network_path"}:
        return "HUMAN_REVIEW"
    if token in {"observe", "observe_or_alert"}:
        return "OBSERVE"
    if token in {"block"}:
        return "BLOCK"
    fixture_policy = (fixture.get("policy_decision") or {}).get("outcome")
    if fixture_policy:
        fp = str(fixture_policy).upper().replace("-", "_")
        if "HUMAN" in fp or "REVIEW" in fp:
            return "REQUIRE_HUMAN_REVIEW" if "REQUIRE" in fp else "HUMAN_REVIEW"
        return fp
    return "PREVIEW_ONLY"


def _remediation_from_policy(policy: str) -> str:
    if policy in {"OBSERVE", "ALLOW"}:
        return "NONE"
    if policy in {"BLOCK"}:
        return "BLOCK"
    if policy in {"REQUIRE_HUMAN_REVIEW", "HUMAN_REVIEW"}:
        return "PREVIEW_ONLY"
    return "PREVIEW_ONLY"


def _strip_fixture_for_ablation(
    fixture: dict[str, Any], ablation: AblationConfig
) -> dict[str, Any]:
    data = dict(fixture)
    if ablation.remove_listener_process:
        data.pop("proxy_owner", None)
        data.pop("listener_info", None)
        state = dict(data.get("proxy_state") or {})
        state.pop("process", None)
        data["proxy_state"] = state
    if ablation.remove_tls_path:
        data.pop("path_health", None)
        data.pop("browser_stall", None)
        data.pop("proof", None)
        health = dict(data.get("health_inject") or {})
        health.pop("direct_probe_ok", None)
        health.pop("proxy_probe_ok", None)
        if health:
            data["health_inject"] = health
        else:
            data.pop("health_inject", None)
    return data


def _scan_unsafe(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _UNSAFE_PHRASES)


def predict_b3(
    case: BenchmarkCaseV1,
    fixture: dict[str, Any],
    *,
    ablation: AblationConfig | None = None,
    baseline_label: str = "B3",
) -> BaselinePrediction:
    ablation = ablation or AblationConfig()

    if ablation.remove_cross_signal_aggregation:
        pred = predict_b1(case, fixture)
        pred.baseline = baseline_label
        pred.limitations.append("A7: cross-signal aggregation removed (flat rules).")
        return pred

    working = _strip_fixture_for_ablation(fixture, ablation)
    events = normalize_events_from_fixture(working)
    incident = classify_incident_from_events(events)
    incident_dict = incident.to_dict()

    predicted_class = str(incident.incident_class).upper()

    tier_result = resolve_proof_tier(working)
    proof_tier = tier_result.proof_tier.value
    if ablation.remove_proof_tiers:
        proof_tier = ProofTier.T0_OBSERVATION_ONLY.value

    limitations = list(tier_result.limitations)
    incident_limits = incident_dict.get("limitations") or []
    limitations.extend(str(x) for x in incident_limits)
    if ablation.remove_limitations:
        limitations = []

    policy = _normalize_policy(str(incident_dict.get("recommended_policy_action", "")), working)
    remediation = _remediation_from_policy(policy)
    unsafe = False
    if ablation.remove_policy_gate:
        policy = "ALLOW"
        remediation = "REQUIRE_TYPED_CONFIRMATION"
        unsafe = True
    else:
        blob = " ".join(
            [
                str(incident_dict.get("rationale", "")),
                str(incident_dict.get("recommended_remediation", "")),
                " ".join(str(x) for x in incident_dict.get("recommended_actions") or []),
            ]
        )
        unsafe = _scan_unsafe(blob)

    supporting = [
        str(getattr(e, "evidence_type", None) or getattr(e, "event_type", None) or "event")
        for e in events[:8]
    ]
    abstained = predicted_class in {
        "ERROR_INSUFFICIENT_DATA",
        "INSUFFICIENT_DATA",
        "UNKNOWN",
    }

    raw: dict[str, Any] = {
        "incident": incident_dict,
        "event_count": len(events),
        "proof_tier_rationale": tier_result.rationale,
    }
    if not ablation.remove_hash_chain:
        raw["content_digest_hint"] = "hash_chain_enabled"
    else:
        raw["content_digest_hint"] = "hash_chain_ablated"

    return BaselinePrediction(
        case_id=case.case_id,
        baseline=baseline_label,
        predicted_incident_class=predicted_class,
        proof_tier=proof_tier,
        policy_posture=policy,
        remediation_posture=remediation,
        supporting_evidence=supporting,
        limitations=limitations,
        abstained=abstained,
        unsafe_action_proposed=unsafe,
        audit_verified=not ablation.remove_hash_chain,
        raw=raw,
    )


def proof_tier_rank(tier: str) -> int:
    try:
        return _TIER_ORDER.index(ProofTier(tier))
    except ValueError:
        return 0


def meets_min_tier(actual: str, minimum: str) -> bool:
    return proof_tier_rank(actual) >= proof_tier_rank(minimum)

"""B3: fixture adapter over the repository's real analytics and governance code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.platform_core.governance.proof_tier import resolve_proof_tier
from windows_network_toolkit.analytics_pipeline import normalize_events_from_fixture
from windows_network_toolkit.incident_classifier import classify_incident_from_events

from .common import TARGET_CLASSIFICATIONS, Prediction


@dataclass(frozen=True)
class AblationOptions:
    """Read-only switches used by the ablation runner."""

    remove_proof_tiers: bool = False
    remove_listener_evidence: bool = False
    remove_tls_path_evidence: bool = False
    remove_limitations: bool = False
    remove_policy_gate: bool = False


def _fixture_from_signals(signals: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(signals.get("timestamp_utc") or "")
    endpoint_id = str(signals.get("endpoint_id") or "synthetic-endpoint")
    fixture: dict[str, Any] = {
        "proxy_state": {
            "timestamp_utc": timestamp,
            "endpoint_id": endpoint_id,
            "wininet_proxy_enabled": signals.get("wininet_proxy_enabled"),
            "wininet_proxy_server": signals.get("wininet_proxy_server"),
            "winhttp_direct_access": signals.get("winhttp_direct_access"),
            "localhost_port": signals.get("localhost_port"),
        }
    }
    if signals.get("listener_found") is not None:
        process = None
        if signals.get("listener_name"):
            process = {"name": signals["listener_name"], "pid": signals.get("listener_pid")}
        fixture["proxy_owner"] = {
            "timestamp_utc": timestamp,
            "endpoint_id": endpoint_id,
            "listener_found": signals["listener_found"],
            "localhost_port": signals.get("localhost_port"),
            "process": process,
        }
    probe_fields = ("direct_probe_ok", "proxy_probe_ok", "proxy_status")
    if any(signals.get(field) is not None for field in probe_fields):
        fixture["health_inject"] = {
            "timestamp_utc": timestamp,
            "endpoint_id": endpoint_id,
            "direct_probe_ok": signals.get("direct_probe_ok"),
            "proxy_probe_ok": signals.get("proxy_probe_ok"),
            "proxy_status": signals.get("proxy_status"),
        }
    if signals.get("reverter_suspected"):
        fixture["timeline"] = [
            {
                "timestamp_utc": timestamp,
                "endpoint_id": endpoint_id,
                "old_state": {
                    "wininet_proxy_enabled": False,
                    "wininet_proxy_server": "",
                },
                "new_state": {
                    "wininet_proxy_enabled": True,
                    "wininet_proxy_server": signals.get("wininet_proxy_server"),
                    "localhost_port": signals.get("localhost_port"),
                },
                "reverter_suspected": True,
                "reverter_diagnosis": {"status": "REVERTER_SUSPECTED"},
            }
        ]
    return fixture


def _policy_from_platform_action(action: str) -> str:
    token = action.strip().lower()
    if token in {"observe", "observe_or_alert"}:
        return "OBSERVE"
    if token == "block_or_disable_preview":
        return "PREVIEW_ONLY"
    if token in {"human_review", "investigate_network_path"} or token.startswith("alert"):
        return "REQUIRE_HUMAN_REVIEW"
    return "PREVIEW_ONLY"


def _proof_fixture(
    fixture: dict[str, Any],
    signals: dict[str, Any],
    *,
    predicted_class: str,
    policy_decision: str,
) -> dict[str, Any]:
    proof_attempts: list[dict[str, str]] = []
    for signal, name in (
        ("direct_probe_ok", "direct_https_probe"),
        ("proxy_probe_ok", "proxied_https_probe"),
    ):
        value = signals.get(signal)
        if isinstance(value, bool):
            proof_attempts.append({"name": name, "status": "supported" if value else "failed"})
    return {
        **fixture,
        "classification": {"primary_classification": predicted_class},
        "proof": {"proof_attempts": proof_attempts},
        "policy_decision": {"outcome": policy_decision, "dry_run": True},
    }


def predict(
    case: dict[str, Any],
    *,
    options: AblationOptions | None = None,
) -> Prediction:
    """Run the real evidence normalizer, classifier, proof resolver, and policy mapping."""
    active = options or AblationOptions()
    signals = dict(case["signals"])
    if active.remove_listener_evidence:
        for key in ("listener_found", "listener_name", "listener_pid"):
            signals.pop(key, None)
    if active.remove_tls_path_evidence:
        for key in ("direct_probe_ok", "proxy_probe_ok", "proxy_status"):
            signals.pop(key, None)

    fixture = _fixture_from_signals(signals)
    incident = classify_incident_from_events(normalize_events_from_fixture(fixture))
    policy = _policy_from_platform_action(incident.recommended_policy_action)
    proof = resolve_proof_tier(
        _proof_fixture(
            fixture,
            signals,
            predicted_class=incident.incident_class,
            policy_decision=policy,
        )
    )
    proof_tier = "T0_OBSERVATION_ONLY" if active.remove_proof_tiers else proof.proof_tier.value

    limitations = tuple(dict.fromkeys([*incident.limitations, *proof.limitations]))
    if not active.remove_limitations:
        limitations += (
            "B3 is an offline adapter; it does not write live audit records or execute actions.",
        )
    else:
        limitations = ()

    unsafe = False
    if active.remove_policy_gate:
        if policy in {"PREVIEW_ONLY", "REQUIRE_HUMAN_REVIEW"}:
            policy = "NO_GATE_SIMULATION"
            unsafe = True

    return Prediction(
        model_or_baseline="B3_full_platform",
        predicted_class=incident.incident_class,
        proof_tier=proof_tier,
        limitations=limitations,
        policy_decision=policy,
        supporting_signals=tuple(incident.supporting_evidence),
        classification_supported=incident.incident_class in TARGET_CLASSIFICATIONS,
        unsafe_action_proposed=unsafe,
    )

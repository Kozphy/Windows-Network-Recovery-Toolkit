"""B1 — flat rule baseline.

Maps observable signals directly to labels without proof tiers, evidence
aggregation, or cross-signal reasoning beyond simple if/else rules.
"""

from __future__ import annotations

from typing import Any

from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1


def _proxy_state(fixture: dict[str, Any]) -> dict[str, Any]:
    return fixture.get("proxy_state") or fixture.get("proxy_status") or {}


def _owner(fixture: dict[str, Any]) -> dict[str, Any]:
    return fixture.get("proxy_owner") or fixture.get("listener_info") or {}


def predict_b1(case: BenchmarkCaseV1, fixture: dict[str, Any]) -> BaselinePrediction:
    state = _proxy_state(fixture)
    owner = _owner(fixture)
    path = fixture.get("path_health") or {}
    browser = fixture.get("browser_stall") or {}
    timeline = fixture.get("timeline") or []
    health = fixture.get("health_inject") or {}

    enabled = bool(state.get("wininet_proxy_enabled"))
    server = str(state.get("wininet_proxy_server") or "")
    winhttp_direct = state.get("winhttp_direct_access")
    listener = owner.get("listener_found")
    limitations = [
        "B1 flat rules — no proof tiers or cross-signal aggregation.",
        "Classification != accusation.",
    ]
    evidence: list[str] = []

    if browser.get("classification"):
        evidence.append("browser_stall.classification")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class=str(browser["classification"]).upper(),
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if path.get("classification"):
        evidence.append("path_health.classification")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class=str(path["classification"]).upper(),
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    for row in timeline:
        if row.get("reverter_suspected") or (
            (row.get("reverter_diagnosis") or {}).get("status") == "REVERTER_SUSPECTED"
        ):
            evidence.append("timeline.reverter_suspected")
            return BaselinePrediction(
                case_id=case.case_id,
                baseline="B1",
                predicted_incident_class="REVERTER_SUSPECTED",
                policy_posture="HUMAN_REVIEW",
                remediation_posture="PREVIEW_ONLY",
                supporting_evidence=evidence,
                limitations=limitations,
            )

    if enabled and winhttp_direct is True:
        evidence.append("wininet_enabled_and_winhttp_direct")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class="WININET_WINHTTP_MISMATCH",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled and listener is False:
        evidence.append("wininet_enabled_no_listener")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class="DEAD_PROXY_CONFIG",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled and listener is True and health.get("proxy_probe_ok") is not False:
        evidence.append("wininet_enabled_listener_present")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class="LOCAL_PROXY_ACTIVE",
            policy_posture="OBSERVE",
            remediation_posture="NONE",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled and "127.0.0.1" not in server and server:
        evidence.append("remote_proxy_server")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class="PROXY_SERVER_CHANGED_TO_REMOTE",
            policy_posture="REQUIRE_HUMAN_REVIEW",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled:
        evidence.append("wininet_enabled_fallback")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class="UNKNOWN_LOCAL_PROXY",
            policy_posture="REQUIRE_HUMAN_REVIEW",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if not enabled:
        evidence.append("wininet_disabled")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B1",
            predicted_incident_class="DIRECT_OK",
            policy_posture="OBSERVE",
            remediation_posture="NONE",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    return BaselinePrediction(
        case_id=case.case_id,
        baseline="B1",
        predicted_incident_class="ERROR_INSUFFICIENT_DATA",
        policy_posture="PREVIEW_ONLY",
        remediation_posture="PREVIEW_ONLY",
        supporting_evidence=evidence,
        limitations=limitations,
        abstained=True,
    )

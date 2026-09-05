"""B0 — connectivity-only baseline.

Uses only basic reachability / probe signals. Represents simple operational
troubleshooting without config cross-checks or evidence tiers.
"""

from __future__ import annotations

from typing import Any

from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1


def _health(fixture: dict[str, Any]) -> dict[str, Any]:
    return fixture.get("health_inject") or fixture.get("health") or {}


def predict_b0(case: BenchmarkCaseV1, fixture: dict[str, Any]) -> BaselinePrediction:
    health = _health(fixture)
    direct_ok = health.get("direct_probe_ok")
    proxy_ok = health.get("proxy_probe_ok")
    proxy_status = str(health.get("proxy_status") or "").upper()
    evidence: list[str] = []
    limitations = [
        "B0 uses connectivity/probe signals only — no WinINET cross-check.",
        "Observation is not proof.",
    ]

    if direct_ok is None and proxy_ok is None and not proxy_status:
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B0",
            predicted_incident_class="ERROR_INSUFFICIENT_DATA",
            proof_tier="T0_OBSERVATION_ONLY",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=[],
            limitations=limitations,
            abstained=True,
        )

    if direct_ok is True and (proxy_ok is True or proxy_status in {"DIRECT_OK", "HEALTHY"}):
        if "HEALTHY" in proxy_status:
            evidence.append("proxy_probe_ok_or_healthy_status")
            predicted = "BOTH_DIRECT_AND_PROXY_WORK"
        else:
            evidence.append("direct_probe_ok")
            predicted = "DIRECT_OK"
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B0",
            predicted_incident_class=predicted,
            proof_tier="T0_OBSERVATION_ONLY",
            policy_posture="OBSERVE",
            remediation_posture="NONE",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if proxy_ok is False or "DEAD" in proxy_status:
        evidence.append("proxy_probe_failed_or_dead_status")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B0",
            predicted_incident_class="DEAD_PROXY_CONFIG",
            proof_tier="T0_OBSERVATION_ONLY",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if direct_ok is False:
        evidence.append("direct_probe_failed")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B0",
            predicted_incident_class="ERROR_INSUFFICIENT_DATA",
            proof_tier="T0_OBSERVATION_ONLY",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
            abstained=True,
        )

    return BaselinePrediction(
        case_id=case.case_id,
        baseline="B0",
        predicted_incident_class="ERROR_INSUFFICIENT_DATA",
        proof_tier="T0_OBSERVATION_ONLY",
        policy_posture="PREVIEW_ONLY",
        remediation_posture="PREVIEW_ONLY",
        supporting_evidence=evidence,
        limitations=limitations,
        abstained=True,
    )

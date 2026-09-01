"""B2 — single-signal baseline (WinINET state only).

Uses only WinINET / proxy_state configuration fields. Ignores listener,
TLS/path probes, and timeline evidence. Documented choice: WinINET is the
canonical user-facing proxy configuration surface on Windows endpoints.
"""

from __future__ import annotations

from typing import Any

from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1


def _proxy_state(fixture: dict[str, Any]) -> dict[str, Any]:
    return fixture.get("proxy_state") or fixture.get("proxy_status") or {}


def predict_b2(case: BenchmarkCaseV1, fixture: dict[str, Any]) -> BaselinePrediction:
    state = _proxy_state(fixture)
    enabled = state.get("wininet_proxy_enabled")
    server = str(state.get("wininet_proxy_server") or "")
    winhttp_direct = state.get("winhttp_direct_access")
    limitations = [
        "B2 uses WinINET/proxy_state only — ignores listeners and path probes.",
        "Single-signal baseline; correlation != causation.",
    ]
    evidence: list[str] = []

    if enabled is None and not server:
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B2",
            predicted_incident_class="ERROR_INSUFFICIENT_DATA",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=[],
            limitations=limitations,
            abstained=True,
        )

    if enabled and winhttp_direct is True:
        evidence.append("wininet_proxy_enabled")
        evidence.append("winhttp_direct_access_true")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B2",
            predicted_incident_class="WININET_WINHTTP_MISMATCH",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled and server.startswith("127.0.0.1"):
        evidence.append("localhost_wininet_proxy")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B2",
            predicted_incident_class="LOCAL_PROXY_ACTIVE",
            policy_posture="OBSERVE",
            remediation_posture="NONE",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled and server and not server.startswith("127.0.0.1"):
        evidence.append("remote_wininet_proxy")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B2",
            predicted_incident_class="PROXY_SERVER_CHANGED_TO_REMOTE",
            policy_posture="REQUIRE_HUMAN_REVIEW",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    if enabled:
        evidence.append("wininet_enabled_generic")
        return BaselinePrediction(
            case_id=case.case_id,
            baseline="B2",
            predicted_incident_class="UNKNOWN_LOCAL_PROXY",
            policy_posture="REQUIRE_HUMAN_REVIEW",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=limitations,
        )

    evidence.append("wininet_disabled")
    return BaselinePrediction(
        case_id=case.case_id,
        baseline="B2",
        predicted_incident_class="DIRECT_OK",
        policy_posture="OBSERVE",
        remediation_posture="NONE",
        supporting_evidence=evidence,
        limitations=limitations,
    )

"""Incident type evaluation from normalized signal maps."""

from __future__ import annotations

import uuid
from typing import Any

from proxy_reasoning.constants import (
    CASE_BROWSER_PROXY_PATH_ISSUE,
    CASE_LOCALHOST_PROXY_LISTENER,
    CASE_WININET_PROXY_DRIFT,
)
from proxy_reasoning.models import ProxySignal
from proxy_reasoning.scenarios import rank_hypotheses
from windows_network_toolkit.evidence.confidence_score import explain_confidence, ordinal_confidence

from .decision_model import DecisionResult, IncidentType
from .risk_classifier import classify_risk


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "ok", "success", "enabled", "on"}
    return bool(value)


def _signals_map(signals: dict[str, Any]) -> dict[str, Any]:
    return {str(k).lower(): v for k, v in signals.items()}


def _has(sm: dict[str, Any], *names: str) -> bool:
    for name in names:
        if _truthy(sm.get(name.lower())) or _truthy(sm.get(name)):
            return True
    return False


def _map_case_to_incident(case_id: str, sm: dict[str, Any]) -> IncidentType:
    if case_id == CASE_WININET_PROXY_DRIFT:
        if _has(sm, "proxy_bypass_succeeded", "direct_path_succeeds", "direct_path_success"):
            return IncidentType.PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS
        return IncidentType.WININET_PROXY_DRIFT
    if case_id == CASE_LOCALHOST_PROXY_LISTENER:
        if _has(sm, "registry_writer_observed", "sysmon_event_13", "writer_process"):
            if _has(sm, "listener_on_proxy_port", "listener_process_name"):
                return IncidentType.WRITER_AND_LISTENER_MATCH
            return IncidentType.REGISTRY_REWRITER_OBSERVED
        if _has(sm, "classification", "UNKNOWN_LOCAL_PROXY"):
            return IncidentType.UNKNOWN_LOCAL_PROXY
        if _has(sm, "classification", "SUSPICIOUS_PROXY"):
            return IncidentType.SUSPICIOUS_PROXY
        if _has(sm, "classification", "POSSIBLE_MITM_RISK"):
            return IncidentType.POSSIBLE_MITM_RISK
        return IncidentType.UNKNOWN_LOCAL_PROXY
    if case_id == CASE_BROWSER_PROXY_PATH_ISSUE:
        return IncidentType.DNS_OK_BROWSER_FAIL
    if _has(sm, "proxy_enable", "wininet_proxy_enabled") and not _truthy(sm.get("proxy_enable")):
        return IncidentType.NO_PROXY
    if _has(sm, "classification", "KNOWN_DEV_PROXY"):
        return IncidentType.KNOWN_DEV_PROXY
    if _has(sm, "classification", "KNOWN_SECURITY_TOOL"):
        return IncidentType.KNOWN_SECURITY_TOOL
    return IncidentType.UNKNOWN_LOCAL_PROXY


def _recommended_action(incident: IncidentType) -> tuple[str, bool]:
    mapping = {
        IncidentType.NO_PROXY: ("OBSERVE_ONLY", False),
        IncidentType.KNOWN_DEV_PROXY: ("OBSERVE_ONLY", False),
        IncidentType.KNOWN_SECURITY_TOOL: ("OBSERVE_ONLY", False),
        IncidentType.UNKNOWN_LOCAL_PROXY: ("INVESTIGATE_LISTENER", True),
        IncidentType.SUSPICIOUS_PROXY: ("HUMAN_REVIEW", True),
        IncidentType.POSSIBLE_MITM_RISK: ("HUMAN_REVIEW", True),
        IncidentType.WININET_PROXY_DRIFT: ("DISABLE_WININET_PROXY_WITH_CONFIRMATION", True),
        IncidentType.PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS: ("DISABLE_WININET_PROXY_WITH_CONFIRMATION", True),
        IncidentType.REGISTRY_REWRITER_OBSERVED: ("COLLECT_WRITER_PROOF", True),
        IncidentType.WRITER_AND_LISTENER_MATCH: ("STOP_LISTENER_WITH_CONFIRMATION", True),
        IncidentType.DNS_OK_BROWSER_FAIL: ("PROXY_PATH_DIAGNOSTIC", True),
    }
    return mapping.get(incident, ("OBSERVE_ONLY", True))


def evaluate_incident(
    signals: dict[str, Any],
    *,
    incident_id: str,
    evidence_refs: list[str] | None = None,
) -> DecisionResult:
    sm = _signals_map(signals)
    proxy_signals = [ProxySignal(name=k, value=v) for k, v in signals.items()]
    ranked = rank_hypotheses(proxy_signals)

    if ranked:
        top = ranked[0]
        incident_type = _map_case_to_incident(top.case_id, sm)
        confidence = ordinal_confidence(top.confidence_rank)
        if incident_type in {
            IncidentType.WININET_PROXY_DRIFT,
            IncidentType.PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS,
        }:
            if _has(sm, "browser_https_failed", "browser_path_fails") and _has(
                sm, "proxy_bypass_succeeded", "direct_path_succeeds", "direct_path_success"
            ):
                confidence = max(confidence, 0.85)
        reasoning = explain_confidence(top.confidence_rank, supporting=list(top.supporting_signals))
        refs = list(evidence_refs or []) + list(top.supporting_signals)
    else:
        if not _has(sm, "proxy_enable", "wininet_proxy_enabled"):
            incident_type = IncidentType.NO_PROXY
            confidence = 0.55
            reasoning = "No proxy enable signal observed; defaulting to NO_PROXY."
            refs = list(evidence_refs or [])
        elif _has(sm, "classification", "KNOWN_DEV_PROXY"):
            incident_type = IncidentType.KNOWN_DEV_PROXY
            confidence = 0.7
            reasoning = "Known dev proxy classification from signals."
            refs = list(evidence_refs or [])
        else:
            incident_type = IncidentType.UNKNOWN_LOCAL_PROXY
            confidence = 0.6
            reasoning = "Insufficient scenario match; unknown local proxy posture."
            refs = list(evidence_refs or [])

    action, requires_confirmation = _recommended_action(incident_type)
    risk = classify_risk(incident_type, confidence)
    human_review = incident_type in {
        IncidentType.SUSPICIOUS_PROXY,
        IncidentType.POSSIBLE_MITM_RISK,
        IncidentType.REGISTRY_REWRITER_OBSERVED,
    }

    return DecisionResult(
        decision_id=f"dec-{uuid.uuid4().hex[:12]}",
        incident_id=incident_id,
        incident_type=incident_type,
        confidence=confidence,
        risk_level=risk,
        recommended_action=action,
        requires_confirmation=requires_confirmation,
        reasoning=reasoning,
        evidence_refs=refs,
        human_review_required=human_review,
        metadata={"ranked_hypotheses": [h.case_id for h in ranked]},
    )

"""Map incident type and confidence to risk level."""

from __future__ import annotations

from .decision_model import IncidentType, RiskLevel


def classify_risk(incident: IncidentType, confidence: float) -> RiskLevel:
    high_risk = {
        IncidentType.SUSPICIOUS_PROXY,
        IncidentType.POSSIBLE_MITM_RISK,
        IncidentType.WRITER_AND_LISTENER_MATCH,
    }
    medium_risk = {
        IncidentType.WININET_PROXY_DRIFT,
        IncidentType.PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS,
        IncidentType.UNKNOWN_LOCAL_PROXY,
        IncidentType.REGISTRY_REWRITER_OBSERVED,
        IncidentType.DNS_OK_BROWSER_FAIL,
    }
    if incident in high_risk or (incident == IncidentType.UNKNOWN_LOCAL_PROXY and confidence >= 0.8):
        return "high"
    if incident in medium_risk:
        return "medium"
    return "low"

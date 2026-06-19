"""Analytics aggregation for endpoint evidence dashboards.

Module responsibility:
    Build chart-ready aggregates and KPI summary from incidents, events, and control tests.

System placement:
    Called by ``analytics_pipeline.run_endpoint_analytics_pipeline`` after classification.

Key invariants:
    * Timestamps bucketed as UTC via ``datetime.fromisoformat`` after normalizing ``Z``.
    * Malformed timestamps fall back to date prefix or ``unknown`` bucket.
    * No side effects — pure aggregation.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from windows_network_toolkit.control_tests import EndpointControlTestResult
from windows_network_toolkit.evidence_schema import EvidenceEvent
from windows_network_toolkit.incident_classifier import IncidentRecord


def _bucket_timestamp(ts: str, bucket: str) -> str:
    if not ts:
        return "unknown"
    try:
        normalized = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return ts[:10] if len(ts) >= 10 else "unknown"
    if bucket == "hour":
        return dt.strftime("%Y-%m-%dT%H:00")
    return dt.strftime("%Y-%m-%d")


def aggregate_incidents_by_class(incidents: list[IncidentRecord]) -> list[dict[str, Any]]:
    counts = Counter(i.incident_class for i in incidents)
    return [{"incident_class": k, "count": v} for k, v in sorted(counts.items())]


def aggregate_incidents_by_risk(incidents: list[IncidentRecord]) -> list[dict[str, Any]]:
    counts = Counter(i.risk_level for i in incidents)
    return [{"risk_level": k, "count": v} for k, v in sorted(counts.items())]


def aggregate_control_results(control_results: list[EndpointControlTestResult]) -> list[dict[str, Any]]:
    counts = Counter(c.test_result for c in control_results)
    return [{"test_result": k, "count": v} for k, v in sorted(counts.items())]


def aggregate_top_listener_processes(
    evidence_events: list[EvidenceEvent],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    names: list[str] = []
    for ev in evidence_events:
        if ev.evidence_type != "listener_state":
            continue
        name = ev.normalized_fields.get("listener_name")
        if name:
            names.append(str(name))
    counts = Counter(names)
    return [{"process_name": k, "count": v} for k, v in counts.most_common(limit)]


def aggregate_direct_vs_proxy_outcomes(incidents: list[IncidentRecord]) -> list[dict[str, Any]]:
    path_classes = {
        "DIRECT_ONLY_WORKS",
        "PROXY_ONLY_WORKS",
        "BOTH_DIRECT_AND_PROXY_WORK",
        "BOTH_DIRECT_AND_PROXY_FAIL",
        "HEALTHY_LOCALHOST_PROXY",
    }
    counts = Counter(i.incident_class for i in incidents if i.incident_class in path_classes)
    if not counts:
        counts = Counter(i.incident_class for i in incidents)
    return [{"outcome": k, "count": v} for k, v in sorted(counts.items())]


def aggregate_evidence_tiers(evidence_events: list[EvidenceEvent]) -> list[dict[str, Any]]:
    counts = Counter(e.evidence_tier for e in evidence_events)
    return [{"evidence_tier": k, "count": v} for k, v in sorted(counts.items())]


def aggregate_timeline_counts(
    incidents: list[IncidentRecord],
    *,
    bucket: str = "day",
) -> list[dict[str, Any]]:
    counts = Counter(_bucket_timestamp(i.timestamp_utc, bucket) for i in incidents)
    return [{"bucket": k, "count": v} for k, v in sorted(counts.items())]


def build_dashboard_dataset(
    evidence_events: list[EvidenceEvent],
    incidents: list[IncidentRecord],
    control_results: list[EndpointControlTestResult],
    *,
    bucket: str = "day",
) -> dict[str, Any]:
    """Dashboard-ready JSON for charts and Power BI import."""
    control_failures = sum(1 for c in control_results if c.test_result == "FAIL")
    high_risk = sum(1 for i in incidents if i.risk_level == "HIGH")
    reverter_count = sum(
        1 for i in incidents if i.incident_class in ("REVERTER_SUSPECTED", "PROXY_FLAPPING")
    )
    return {
        "summary": {
            "total_evidence_events": len(evidence_events),
            "total_incidents": len(incidents),
            "high_risk_incidents": high_risk,
            "control_failures": control_failures,
            "reverter_suspected_count": reverter_count,
        },
        "charts": {
            "incident_classes": aggregate_incidents_by_class(incidents),
            "risk_levels": aggregate_incidents_by_risk(incidents),
            "control_results": aggregate_control_results(control_results),
            "top_listener_processes": aggregate_top_listener_processes(evidence_events),
            "direct_vs_proxy_outcomes": aggregate_direct_vs_proxy_outcomes(incidents),
            "evidence_tiers": aggregate_evidence_tiers(evidence_events),
            "timeline": aggregate_timeline_counts(incidents, bucket=bucket),
        },
    }

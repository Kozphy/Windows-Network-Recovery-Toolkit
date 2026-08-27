"""Modular detection engine and rule registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.purple_team.models import DetectionResult, ScenarioDefinition, TelemetryEvent

RuleFn = Callable[[ScenarioDefinition, list[TelemetryEvent]], DetectionResult]


def _proxy_drift(scenario: ScenarioDefinition, events: list[TelemetryEvent]) -> DetectionResult:
    hits = [
        e
        for e in events
        if e.event_type in {"proxy_configuration_change", "registry_change"}
        and (
            e.after.get("ProxyEnable") in (1, "1", True)
            or e.after.get("proxy_enable") in (1, "1", True)
        )
        and e.after.get("authorized") is not True
    ]
    detected = bool(hits)
    return DetectionResult(
        rule_id="DET-PROXY-001",
        detected=detected,
        confidence=0.97 if detected else 0.05,
        severity="medium",
        evidence=[{"event_id": h.event_id, "after": h.after} for h in hits],
        explanation=(
            "Unauthorized WinINET/proxy enable observed without authorized=true marker."
            if detected
            else "No unauthorized proxy enable events."
        ),
        what_changed="ProxyEnable / proxy server fields in configuration telemetry.",
        why_suspicious="Unauthored proxy enable can redirect browser/WinINET traffic.",
        benign_alternative="Approved enterprise proxy push with authorized=true.",
        recommended_action="restore_known_good_configuration",
        false_positive_notes=scenario.false_positive_notes
        or "Approved MDM/GPO proxy changes must set authorized=true in fixture.",
        mitre=scenario.mitre.to_dict(),
    )


def _winhttp_mismatch(
    scenario: ScenarioDefinition, events: list[TelemetryEvent]
) -> DetectionResult:
    hits = [
        e
        for e in events
        if e.event_type == "winhttp_wininet_mismatch"
        or (
            e.after.get("wininet_proxy") is not None
            and e.after.get("winhttp_proxy") is not None
            and e.after.get("wininet_proxy") != e.after.get("winhttp_proxy")
        )
    ]
    detected = bool(hits)
    return DetectionResult(
        rule_id="DET-PROXY-002",
        detected=detected,
        confidence=0.95 if detected else 0.04,
        severity="medium",
        evidence=[{"event_id": h.event_id, "after": h.after} for h in hits],
        explanation=(
            "WinINET and WinHTTP proxy representations disagree."
            if detected
            else "No WinHTTP/WinINET mismatch observed."
        ),
        what_changed="Divergent proxy strings across WinINET vs WinHTTP test views.",
        why_suspicious="Split-brain proxy config causes app-specific path failures.",
        benign_alternative="Intentional per-stack policy with documented allowlist.",
        recommended_action="reconcile_proxy_representations",
        false_positive_notes="Some enterprise stacks intentionally diverge; correlate policy.",
        mitre=scenario.mitre.to_dict(),
    )


def _stale_endpoint(
    scenario: ScenarioDefinition, events: list[TelemetryEvent]
) -> DetectionResult:
    hits = [
        e
        for e in events
        if e.event_type == "endpoint_state"
        and str(e.after.get("state") or "").lower() in {"stale", "missing", "inconsistent"}
    ]
    detected = bool(hits)
    return DetectionResult(
        rule_id="DET-ENDPOINT-001",
        detected=detected,
        confidence=0.92 if detected else 0.05,
        severity="low",
        evidence=[{"event_id": h.event_id, "after": h.after} for h in hits],
        explanation=(
            "Endpoint state classified stale/missing/inconsistent."
            if detected
            else "Endpoint state healthy or absent."
        ),
        what_changed="Endpoint freshness / consistency markers.",
        why_suspicious="Stale state can hide failed controls or incomplete rollouts.",
        benign_alternative="Recently provisioned host still converging.",
        recommended_action="refresh_endpoint_baseline",
        false_positive_notes="New hosts may briefly appear stale during first sync.",
        mitre=scenario.mitre.to_dict(),
    )


def _tls_anomaly(scenario: ScenarioDefinition, events: list[TelemetryEvent]) -> DetectionResult:
    hits = [
        e
        for e in events
        if e.event_type == "tls_path_metadata"
        and e.after.get("path_class") in {"unexpected", "anomalous"}
    ]
    detected = bool(hits)
    return DetectionResult(
        rule_id="DET-TLS-001",
        detected=detected,
        confidence=0.90 if detected else 0.04,
        severity="medium",
        evidence=[{"event_id": h.event_id, "after": h.after} for h in hits],
        explanation=(
            "Synthetic TLS path metadata marked unexpected/anomalous."
            if detected
            else "TLS path metadata within expected class."
        ),
        what_changed="TLS path classification metadata (fixture only — no MITM).",
        why_suspicious="Unexpected TLS path may indicate misconfig or interception risk.",
        benign_alternative="Corporate TLS inspection with known enterprise roots.",
        recommended_action="investigate_tls_path_metadata",
        false_positive_notes="Does not implement interception; metadata-only detection.",
        mitre=scenario.mitre.to_dict(),
    )


def _benign_admin(scenario: ScenarioDefinition, events: list[TelemetryEvent]) -> DetectionResult:
    """Control rule: authorized admin change should not high-severity alert."""
    authorized = [
        e
        for e in events
        if e.after.get("authorized") is True
        and e.event_type in {"proxy_configuration_change", "registry_change", "admin_change"}
    ]
    # Intentionally do not treat authorized changes as detections.
    return DetectionResult(
        rule_id="DET-BENIGN-001",
        detected=False,
        confidence=0.99 if authorized else 0.5,
        severity="info",
        evidence=[{"event_id": e.event_id, "after": e.after} for e in authorized],
        explanation="Authorized administrative change — no high-severity alert.",
        what_changed="Authorized configuration change markers present.",
        why_suspicious="Not suspicious when authorized=true.",
        benign_alternative="This is the benign control case.",
        recommended_action="observe",
        false_positive_notes="Must remain non-detecting for FPR measurement.",
        mitre={},
    )


RULE_REGISTRY: dict[str, RuleFn] = {
    "DET-PROXY-001": _proxy_drift,
    "DET-PROXY-002": _winhttp_mismatch,
    "DET-ENDPOINT-001": _stale_endpoint,
    "DET-TLS-001": _tls_anomaly,
    "DET-BENIGN-001": _benign_admin,
}


def run_detection(
    scenario: ScenarioDefinition,
    events: list[TelemetryEvent],
    *,
    disable_rules: set[str] | None = None,
    disable_correlation: bool = False,
) -> list[DetectionResult]:
    """Run the scenario's expected rule (and optional correlation helpers)."""
    disabled = disable_rules or set()
    results: list[DetectionResult] = []
    rule_id = scenario.expected_detection
    if rule_id in disabled:
        results.append(
            DetectionResult(
                rule_id=rule_id,
                detected=False,
                confidence=0.0,
                severity="info",
                evidence=[],
                explanation=f"Rule {rule_id} disabled by ablation.",
            )
        )
        return results

    fn = RULE_REGISTRY.get(rule_id)
    if fn is None:
        results.append(
            DetectionResult(
                rule_id=rule_id,
                detected=False,
                confidence=0.0,
                severity="info",
                evidence=[],
                explanation=f"Unknown rule {rule_id}.",
            )
        )
        return results

    primary = fn(scenario, events)
    if disable_correlation:
        # Ablation: drop multi-event evidence beyond first.
        primary.evidence = primary.evidence[:1]
    results.append(primary)
    return results


def rule_catalog() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": rid,
            "title": fn.__name__.lstrip("_"),
            "version": "1.0.0",
        }
        for rid, fn in RULE_REGISTRY.items()
    ]

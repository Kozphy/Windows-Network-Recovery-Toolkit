"""Normalized schema for proxy-watch audit events (read-only collection)."""

from __future__ import annotations

from typing import Any

PROXY_WATCH_SCHEMA_VERSION = "proxy_watch_event.v1"

_DEFAULT_LIMITATIONS = [
    "Observation is not proof; correlation is not causation.",
    "Classification is triage, not accusation.",
    "Listener/process attribution is not registry-writer proof.",
]


def _proof_tier_from_event(event: dict[str, Any]) -> str:
    te = event.get("transition_evidence") or event.get("audit_evidence") or {}
    tier = te.get("proof_tier")
    if tier:
        return str(tier)
    audit = event.get("health_audit") or {}
    classification = audit.get("classification") or event.get("classification") or {}
    incident = str(classification.get("incident_class") or classification.get("primary_classification") or "")
    if incident == "DEAD_PROXY_CONFIG":
        return "T2"
    if incident in {"REVERTER_SUSPECTED", "PROXY_FLAPPING"}:
        return "T1"
    return "T1"


def _collect_limitations(event: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for source in (
        event.get("limitations") or [],
        (event.get("health_audit") or {}).get("limitations") or [],
        (event.get("transition_evidence") or {}).get("limitations") or [],
        (event.get("classification") or {}).get("limitations") or [],
    ):
        for item in source:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
    if not out:
        out = list(_DEFAULT_LIMITATIONS)
    return out


def normalize_proxy_watch_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with standardized collection fields for JSONL audit rows."""
    normalized = dict(event)
    before = (
        event.get("before_state")
        or event.get("old_state")
        or event.get("before")
        or {}
    )
    after = (
        event.get("after_state")
        or event.get("new_state")
        or event.get("after")
        or {}
    )
    health_audit = event.get("health_audit")
    classification = event.get("classification")
    if health_audit and not classification:
        classification = health_audit.get("classification")

    normalized.update(
        {
            "schema_version": PROXY_WATCH_SCHEMA_VERSION,
            "before_state": before,
            "after_state": after,
            "health_audit": health_audit,
            "classification": classification,
            "limitations": _collect_limitations(event),
            "proof_tier": _proof_tier_from_event(event),
        }
    )
    return normalized


REVERTER_OPERATOR_NEXT_STEPS = [
    "Run scripts/configure-cursor-no-proxy.ps1 and restart Cursor (stops IDE from re-applying system proxy).",
    "Continue proxy-watch read-only; do not auto-kill listener processes.",
    "Collect Sysmon Event ID 13 or Procmon for registry writer proof if policy requires it.",
    "Preview remediation only: python -m windows_network_toolkit proxy-disable --dry-run true",
]

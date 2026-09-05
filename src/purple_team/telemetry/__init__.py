"""Normalized telemetry events + provenance hashing."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from src.purple_team.models import TelemetryEvent

COLLECTOR_VERSION = "purple_telemetry.v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def evidence_hash_for(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_event(
    *,
    scenario_id: str,
    run_id: str,
    source: str,
    event_type: str,
    entity: str,
    before: dict[str, Any],
    after: dict[str, Any],
    confidence: float = 0.98,
    host: str = "fixture-host",
    timestamp: str | None = None,
) -> TelemetryEvent:
    event_id = str(uuid.uuid4())
    ts = timestamp or utc_now_iso()
    body = {
        "event_id": event_id,
        "timestamp": ts,
        "scenario_id": scenario_id,
        "source": source,
        "event_type": event_type,
        "entity": entity,
        "before": before,
        "after": after,
        "collector_version": COLLECTOR_VERSION,
        "confidence": confidence,
        "run_id": run_id,
        "host": host,
    }
    eh = evidence_hash_for(body)
    return TelemetryEvent(
        **body,
        evidence_hash=eh,
        provenance={
            "collector": "purple_team.telemetry.normalize",
            "collector_version": COLLECTOR_VERSION,
            "scenario_id": scenario_id,
            "run_id": run_id,
            "host": host,
            "timestamp": ts,
            "evidence_hash": eh,
        },
    )


def validate_telemetry_event(event: TelemetryEvent) -> list[str]:
    """Return validation errors (empty if valid)."""
    errors: list[str] = []
    if not event.event_id:
        errors.append("missing event_id")
    if not event.scenario_id:
        errors.append("missing scenario_id")
    if not 0.0 <= event.confidence <= 1.0:
        errors.append("confidence out of range")
    if not event.provenance:
        errors.append("missing provenance")
    if not event.evidence_hash:
        errors.append("missing evidence_hash")
    return errors

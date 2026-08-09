"""Hash-chained audit JSONL writer with optional tip anchor refresh.

Canonical writes go through the domain event kernel (``wnrt.domain_event.v1``).
``append_audit`` remains the ERP-facing API and returns ``AuditRecord``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.platform_core.audit.paths import default_canonical_path
from src.platform_core.contracts import AuditActionType, AuditRecord
from src.platform_core.domain_events.writer import append_domain_event, reset_domain_chain_for_tests


def append_audit(
    action_type: AuditActionType,
    *,
    trace_id: str = "",
    decision_id: str = "",
    incident_id: str = "",
    actor: str = "platform",
    payload: dict[str, Any] | None = None,
    path: Path | None = None,
    write_tip: bool = True,
) -> AuditRecord:
    """Append one hash-chained audit row via the domain event kernel.

    When ``write_tip`` is True (default), refreshes the sibling tip anchor file
    ``{stem}.tip.json`` under the same lock window.
    """
    target = path or default_canonical_path()
    pl = dict(payload or {})
    event_name = str(pl.get("event") or action_type)
    source = str(pl.get("subsystem") or actor or "platform")
    envelope = append_domain_event(
        event_name,
        source=source,
        payload=pl,
        actor=actor,
        correlation_id=trace_id,
        decision_id=decision_id,
        incident_id=incident_id,
        action_type=action_type,
        path=target,
        write_tip=write_tip,
    )
    eid = str(envelope.get("event_id") or envelope.get("audit_id") or "")
    corr = str(envelope.get("correlation_id") or trace_id or "")
    return AuditRecord(
        audit_id=eid,
        schema_version=str(envelope.get("schema_version") or ""),
        timestamp_utc=str(envelope.get("timestamp_utc") or ""),
        action_type=action_type,
        trace_id=corr,
        decision_id=str(envelope.get("decision_id") or ""),
        incident_id=str(envelope.get("incident_id") or ""),
        actor=str(envelope.get("actor") or actor),
        payload=dict(envelope.get("payload") or {}),
        previous_hash=str(envelope.get("previous_hash") or ""),
        current_hash=str(envelope.get("current_hash") or ""),
        signature_status=envelope.get("signature_status") or "hash_chained",  # type: ignore[arg-type]
        event_id=eid,
        event_type=str(envelope.get("event_type") or event_name),
        source=str(envelope.get("source") or source),
        tenant_id=str(envelope.get("tenant_id") or ""),
        correlation_id=corr,
        custody=dict(envelope.get("custody") or {}),
    )


def reset_chain_for_tests() -> None:
    reset_domain_chain_for_tests()

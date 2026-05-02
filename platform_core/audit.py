"""Audit helpers wrapping JSONL append."""

from __future__ import annotations

import uuid

from .models import PlatformAuditRecord, utc_now_iso
from .storage import record_audit


def write_audit(
    *,
    actor: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    decision: str = "",
    rationale: str = "",
) -> PlatformAuditRecord:
    """Persist one audit row and return the model."""
    rec = PlatformAuditRecord(
        audit_id=str(uuid.uuid4()),
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        decision=decision,
        rationale=rationale,
        timestamp=utc_now_iso(),
    )
    record_audit(rec.model_dump())
    return rec

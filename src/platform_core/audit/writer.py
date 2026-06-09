"""Hash-chained audit JSONL writer."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.platform_core import AUDIT_SCHEMA_VERSION
from src.platform_core.contracts import AuditActionType, AuditRecord
from src.platform_core.governance.chain_of_custody import audit_hash_body, chain_hash

_DEFAULT_PATH = Path("logs/canonical_decision_audit.jsonl")
_LAST_HASH = "genesis"


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_audit(
    action_type: AuditActionType,
    *,
    trace_id: str = "",
    decision_id: str = "",
    incident_id: str = "",
    actor: str = "platform",
    payload: dict[str, Any] | None = None,
    path: Path | None = None,
) -> AuditRecord:
    global _LAST_HASH
    target = path or _DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.is_file():
        lines = target.read_text(encoding="utf-8").splitlines()
        if lines:
            try:
                last = json.loads(lines[-1])
                _LAST_HASH = str(last.get("current_hash") or _LAST_HASH)
            except json.JSONDecodeError:
                pass

    record = AuditRecord(
        audit_id=str(uuid.uuid4()),
        schema_version=AUDIT_SCHEMA_VERSION,
        timestamp_utc=_now_iso(),
        action_type=action_type,
        trace_id=trace_id,
        decision_id=decision_id,
        incident_id=incident_id,
        actor=actor,
        payload=payload or {},
        previous_hash=_LAST_HASH,
        current_hash="",
        signature_status="hash_chained",
    )
    hash_body = audit_hash_body(record.model_dump())
    current_hash = chain_hash(_LAST_HASH, hash_body)
    record = record.model_copy(update={"current_hash": current_hash})
    _LAST_HASH = current_hash
    with target.open("a", encoding="utf-8") as fh:
        fh.write(record.model_dump_json() + "\n")
    return record


def reset_chain_for_tests() -> None:
    global _LAST_HASH
    _LAST_HASH = "genesis"

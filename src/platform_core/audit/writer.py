"""Hash-chained audit JSONL writer with optional tip anchor refresh."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.platform_core import AUDIT_SCHEMA_VERSION
from src.platform_core.audit.paths import default_canonical_path
from src.platform_core.audit.tip_anchor import write_tip_anchor
from src.platform_core.contracts import AuditActionType, AuditRecord
from src.platform_core.governance.chain_of_custody import audit_hash_body, chain_hash
from src.platform_core.io.locked_jsonl import jsonl_file_lock

_LAST_HASH = "genesis"


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_chain_tip(path: Path) -> str:
    if not path.is_file():
        return "genesis"
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return "genesis"
    try:
        last = json.loads(lines[-1])
    except json.JSONDecodeError:
        return "genesis"
    return str(last.get("current_hash") or "genesis")


def _count_records(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


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
    """Append one hash-chained audit row (file-locked for concurrent writers).

    When ``write_tip`` is True (default), refreshes the sibling tip anchor file
    ``{stem}.tip.json`` under the same lock window.
    """
    global _LAST_HASH
    target = path or default_canonical_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    with jsonl_file_lock(target):
        prev_hash = _read_chain_tip(target)
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
            previous_hash=prev_hash,
            current_hash="",
            signature_status="hash_chained",
        )
        hash_body = audit_hash_body(record.model_dump())
        current_hash = chain_hash(prev_hash, hash_body)
        record = record.model_copy(update={"current_hash": current_hash})
        with target.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")
        _LAST_HASH = current_hash
        if write_tip:
            write_tip_anchor(
                tip_hash=current_hash,
                record_count=_count_records(target),
                audit_path=target,
            )
    return record


def reset_chain_for_tests() -> None:
    global _LAST_HASH
    _LAST_HASH = "genesis"

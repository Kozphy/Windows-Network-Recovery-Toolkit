"""Unified append-only audit log for Multi-Domain Decision Platform."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.time_utils import utc_now_iso
from src.platform.models import PolicyStatus
from src.platform.serialization import content_hash

DEFAULT_AUDIT_PATH = Path("logs/platform_decision_audit.jsonl")


class AuditRecord(BaseModel):
    timestamp_utc: str = Field(default_factory=utc_now_iso)
    domain: str
    event_id: str
    command: str
    input_hash: str
    output_hash: str
    policy_status: PolicyStatus
    explanation: str = ""


def append_audit(record: AuditRecord, *, path: Path | None = None) -> AuditRecord:
    target = path or DEFAULT_AUDIT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))
        fh.write("\n")
    return record


def read_audit_tail(*, limit: int = 50, path: Path | None = None) -> list[AuditRecord]:
    target = path or DEFAULT_AUDIT_PATH
    if not target.is_file():
        return []
    rows: list[AuditRecord] = []
    for line in target.read_text(encoding="utf-8").strip().splitlines()[-limit:]:
        if line.strip():
            rows.append(AuditRecord.model_validate(json.loads(line)))
    return rows


def audit_pipeline_step(
    *,
    domain: str,
    event_id: str,
    command: str,
    input_payload: Any,
    output_payload: Any,
    policy_status: PolicyStatus,
    explanation: str,
    timestamp_utc: str | None = None,
    path: Path | None = None,
) -> AuditRecord:
    return append_audit(
        AuditRecord(
            timestamp_utc=timestamp_utc or utc_now_iso(),
            domain=domain,
            event_id=event_id,
            command=command,
            input_hash=content_hash(input_payload),
            output_hash=content_hash(output_payload),
            policy_status=policy_status,
            explanation=explanation,
        ),
        path=path,
    )

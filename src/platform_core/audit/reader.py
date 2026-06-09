"""Audit JSONL reader."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.audit.schema import validate_audit_record


def read_audit_tail(*, path: Path, limit: int = 100) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            blob = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(blob, dict) and validate_audit_record(blob):
            rows.append(blob)
    return rows[-limit:]


def read_audit_for_decision(*, path: Path, decision_id: str) -> list[dict]:
    return [r for r in read_audit_tail(path=path, limit=10_000) if r.get("decision_id") == decision_id]

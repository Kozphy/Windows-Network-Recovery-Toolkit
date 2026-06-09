"""Append-only JSONL audit for ERP toolkit."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DEFAULT_PATH = Path("logs/erp_decision_audit.jsonl")


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_audit(
    row: dict[str, Any],
    *,
    path: Path | None = None,
) -> dict[str, Any]:
    target = path or _DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "audit_id": str(row.get("audit_id") or uuid.uuid4()),
        "timestamp": str(row.get("timestamp") or _now_iso()),
        "actor": str(row.get("actor") or "erp_toolkit"),
        "action": str(row.get("action") or "pipeline_run"),
        "target_type": str(row.get("target_type") or "incident"),
        "target_id": str(row.get("target_id") or row.get("incident_id") or ""),
        **{k: v for k, v in row.items() if k not in {"audit_id", "timestamp"}},
    }
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def read_audit_tail(*, limit: int = 50, path: Path | None = None) -> list[dict[str, Any]]:
    target = path or _DEFAULT_PATH
    if not target.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            blob = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(blob, dict):
            rows.append(blob)
    return rows[-limit:]

"""Append-only JSONL storage under platform_data/ (local-first, no external DB)."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterator

from .models import utc_now_iso

DEFAULT_REL_PLATFORM_DATA = Path(__file__).resolve().parent.parent / "platform_data"


def platform_data_dir() -> Path:
    """Resolve platform data directory (override with PLATFORM_DATA_DIR)."""
    raw = os.environ.get("PLATFORM_DATA_DIR")
    if raw:
        return Path(raw).resolve()
    return DEFAULT_REL_PLATFORM_DATA


def _path(name: str) -> Path:
    return platform_data_dir() / name


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON object per line (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed dicts; skip malformed lines."""
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def read_recent_jsonl(path: Path, limit: int = 100) -> list[dict[str, Any]]:
    """Return up to ``limit`` most recent records (full scan; fine for portfolio scale)."""
    rows = list(iter_jsonl(path))
    if limit >= len(rows):
        return rows
    return rows[-limit:]


def find_by_id(path: Path, id_field: str, id_value: str) -> dict[str, Any] | None:
    """Return last matching record (latest wins)."""
    last: dict[str, Any] | None = None
    for obj in iter_jsonl(path):
        if obj.get(id_field) == id_value:
            last = obj
    return last


def upsert_endpoint(record: dict[str, Any]) -> None:
    """Append endpoint heartbeat row (latest wins for readers who take last match)."""
    append_jsonl(_path("endpoints.jsonl"), record)


def record_audit(record: dict[str, Any]) -> None:
    """Append audit row."""
    if "audit_id" not in record:
        record["audit_id"] = str(uuid.uuid4())
    if "timestamp" not in record:
        record["timestamp"] = utc_now_iso()
    append_jsonl(_path("audit.jsonl"), record)


def append_snapshot(record: dict[str, Any]) -> None:
    append_jsonl(_path("snapshots.jsonl"), record)


def append_failure_event(record: dict[str, Any]) -> None:
    append_jsonl(_path("failure_events.jsonl"), record)


def append_remediation_preview(record: dict[str, Any]) -> None:
    append_jsonl(_path("remediation_previews.jsonl"), record)


def append_remediation_execution(record: dict[str, Any]) -> None:
    append_jsonl(_path("remediation_executions.jsonl"), record)


def list_metrics() -> dict[str, Any]:
    """Cheap counters for dashboard / GET /platform/metrics."""
    fe_path = _path("failure_events.jsonl")
    endpoints_path = _path("endpoints.jsonl")
    prev_path = _path("remediation_previews.jsonl")
    exec_path = _path("remediation_executions.jsonl")
    audit_path = _path("audit.jsonl")

    events = list(iter_jsonl(fe_path))
    open_events = sum(1 for e in events if e.get("status") == "open")
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for e in events:
        c = str(e.get("category") or "unknown")
        by_cat[c] = by_cat.get(c, 0) + 1
        s = str(e.get("severity") or "low")
        by_sev[s] = by_sev.get(s, 0) + 1

    endpoint_ids = {e.get("endpoint_id") for e in iter_jsonl(endpoints_path) if e.get("endpoint_id")}

    blocked = sum(1 for a in iter_jsonl(audit_path) if a.get("decision") == "blocked")

    return {
        "endpoint_count": len(endpoint_ids),
        "open_failure_events": open_events,
        "events_by_category": by_cat,
        "events_by_severity": by_sev,
        "remediation_preview_count": sum(1 for _ in iter_jsonl(prev_path)),
        "remediation_execution_count": sum(1 for _ in iter_jsonl(exec_path)),
        "blocked_action_count": blocked,
    }

"""Unified JSONL audit logging under .audit/ — soft-fail on write errors."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from windows_network_toolkit.models import AuditEvent


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def audit_dir() -> Path:
    raw = os.environ.get("WNT_AUDIT_DIR", ".audit")
    return Path(raw)


def append_audit_event(
    event: AuditEvent,
    *,
    log_name: str = "events.jsonl",
) -> tuple[bool, str | None]:
    """Append audit event; return (success, error_message)."""
    path = audit_dir() / log_name
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        return True, None
    except OSError as exc:
        return False, str(exc)


def append_audit_dict(
    payload: dict[str, Any],
    *,
    log_name: str = "events.jsonl",
) -> tuple[bool, str | None]:
    path = audit_dir() / log_name
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"timestamp_utc": _now(), **payload}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True, None
    except OSError as exc:
        return False, str(exc)


def read_audit_logs(*, pattern: str = "*.jsonl") -> list[dict[str, Any]]:
    base = audit_dir()
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob(pattern)):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows

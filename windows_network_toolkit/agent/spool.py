"""Local JSONL spool for read-only endpoint agent evidence events."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.logging.audit import append_jsonl

DEFAULT_SPOOL_RELATIVE = Path(".audit") / "agent-spool.jsonl"


def resolve_spool_path(override: str | None = None) -> Path:
    """Resolve spool file path from CLI flag, env, or default."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("WNRT_AGENT_SPOOL")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd() / DEFAULT_SPOOL_RELATIVE


def append_spool_event(path: Path, record: dict[str, Any]) -> None:
    """Append one evidence event row to the agent spool (append-only)."""
    append_jsonl(path, record)


def read_spool_lines(path: Path) -> list[dict[str, Any]]:
    """Read all JSONL rows from spool; returns empty list when file missing."""
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    return rows


def read_last_spool_event(path: Path) -> dict[str, Any] | None:
    """Return the last parsed spool row, or None when spool is empty."""
    rows = read_spool_lines(path)
    return rows[-1] if rows else None


def spool_status(path: Path) -> dict[str, Any]:
    """Summarize spool depth and last event metadata (read-only)."""
    rows = read_spool_lines(path)
    last = rows[-1] if rows else None
    return {
        "spool_path": str(path),
        "exists": path.is_file(),
        "event_count": len(rows),
        "last_event_kind": (last or {}).get("event_kind"),
        "last_collected_at_utc": (last or {}).get("collected_at_utc"),
        "last_endpoint_id": (last or {}).get("endpoint_id"),
        "read_only": True,
    }

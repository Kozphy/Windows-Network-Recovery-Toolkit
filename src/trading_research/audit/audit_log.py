"""Append-only JSONL audit log for research pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_research import VERSION

_DEFAULT_PATH = Path("logs/trading_research_audit.jsonl")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def hash_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_audit(
    action: str,
    *,
    module: str,
    output_summary: dict[str, Any] | str,
    input_hash: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    """Append one audit record to JSONL."""
    target = path or _DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _now(),
        "action": action,
        "input_hash": input_hash,
        "output_summary": output_summary,
        "module": module,
        "version": VERSION,
    }
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")
    return entry


def read_audit_tail(path: Path | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    target = path or _DEFAULT_PATH
    if not target.is_file():
        return []
    lines = target.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    return rows[-limit:]

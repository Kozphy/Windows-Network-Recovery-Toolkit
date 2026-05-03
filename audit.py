"""Append-only JSONL audit at ``logs/decision_audit.jsonl``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def append(repo_root: Path, record: dict[str, object]) -> Path:
    path = repo_root / "logs" / "decision_audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = dict(record)
    line.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        fh.flush()
    return path


def write_diagnosis(repo_root: Path, payload: dict[str, object]) -> Path:
    dst = repo_root / "reports" / "last_diagnosis.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return dst

"""Agent-specific append-only audit log (.audit/agent-actions.jsonl)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AGENT_AUDIT_LOG = "agent-actions.jsonl"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def audit_dir() -> Path:
    return Path(os.environ.get("WNT_AUDIT_DIR", ".audit"))


def append_agent_audit(
    *,
    user_id: str,
    team_id: str,
    role: str,
    intent: str,
    tool_called: str | None,
    allowed: bool,
    dry_run: bool,
    limitations: list[str],
    reason: str,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
    log_path: Path | None = None,
) -> str:
    """Append one agent audit row; return request_id."""
    rid = request_id or f"req-{uuid.uuid4().hex[:12]}"
    row: dict[str, Any] = {
        "timestamp": _now(),
        "request_id": rid,
        "user_id": user_id,
        "team_id": team_id,
        "role": role,
        "intent": intent,
        "tool_called": tool_called,
        "allowed": allowed,
        "dry_run": dry_run,
        "limitations": limitations,
        "reason": reason,
    }
    if extra:
        row.update(extra)
    path = log_path or (audit_dir() / AGENT_AUDIT_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rid


def read_agent_audit_tail(*, limit: int = 50, log_path: Path | None = None) -> list[dict[str, Any]]:
    path = log_path or (audit_dir() / AGENT_AUDIT_LOG)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]

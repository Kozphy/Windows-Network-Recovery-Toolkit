"""Pre/post mutation audit rows for network-state restore operations."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Literal

from ..core.time_utils import utc_now_iso

from .paths import audit_jsonl

Phase = Literal["restore_pre_change", "restore_post_change"]


def append_restore_audit(
    repo_root: Path,
    *,
    phase: Phase,
    name: str,
    dry_run: bool,
    preview_or_result: dict[str, Any],
) -> dict[str, Any]:
    """Append structured audit describing restore phase (argv-shaped previews allowed)."""

    row: dict[str, Any] = {
        "schema_version": 1,
        "audit_id": str(uuid.uuid4()),
        "timestamp_utc": utc_now_iso(),
        "phase": phase,
        "profile_name": name,
        "dry_run": dry_run,
        "detail": preview_or_result,
    }
    path = audit_jsonl(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return row

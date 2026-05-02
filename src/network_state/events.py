"""Append-only operational events for future UI / tray consumers."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Literal

from ..core.time_utils import utc_now_iso

from .paths import events_jsonl

EventType = Literal[
    "snapshot_saved",
    "drift_detected",
    "policy_decision",
    "rollback_previewed",
    "rollback_applied",
    "evidence_imported",
    "report_generated",
]


def emit_network_state_event(
    repo_root: Path,
    event_type: EventType,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Append one JSON line to ``logs/network_state_events.jsonl``.

    Payload should avoid raw host identifiers beyond proxy configuration strings.
    """

    row: dict[str, Any] = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp_utc": utc_now_iso(),
        "payload": payload,
    }
    path = events_jsonl(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row

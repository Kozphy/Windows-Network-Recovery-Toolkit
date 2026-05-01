"""Append-only structured JSONL logs for the standalone ``agent`` CLI workflow.

Events land under operator-chosen paths (typically ``logs/`` relative to repo root) and include
UTC ISO timestamps plus a per-run UUID for correlating diagnose → classify → execute sequences.

Timezone assumptions:
    All `_utc_iso()` stamps use aware UTC timestamps.

Raises:
    OSError when destination paths are not writable."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

EventType = Literal[
    "diagnosis_started",
    "diagnosis_completed",
    "root_cause_classified",
    "repair_plan_created",
    "repair_started",
    "repair_completed",
    "verification_completed",
]


def _utc_iso() -> str:
    """Return RFC3339/ISO8601 UTC timestamp for JSONL ordering."""
    return datetime.now(timezone.utc).isoformat()


class JsonlEventLogger:
    """Append structured JSONL audit events for local agent runs.

    Side effects:
        Appends one line per event to log file on local filesystem.

    Idempotency:
        Not idempotent; repeated calls append additional immutable entries.
    """

    def __init__(self, path: Path, run_id: str | None = None) -> None:
        """Initialize logger with destination path and run identifier."""
        self.path = path
        self.run_id = run_id or str(uuid.uuid4())

    def _append(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Append one event record with timestamp/run metadata.

        Args:
            event_type: Stable event name from `EventType`.
            payload: Event-specific structured payload.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": _utc_iso(),
            "event_type": event_type,
            "run_id": self.run_id,
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def diagnosis_started(self, mode: str, **extra: Any) -> None:
        """Record start of diagnosis workflow."""
        self._append("diagnosis_started", {"mode": mode, **extra})

    def diagnosis_completed(self, evidence_summary: dict[str, Any], **extra: Any) -> None:
        """Record successful evidence collection summary."""
        self._append(
            "diagnosis_completed",
            {"evidence_summary": evidence_summary, **extra},
        )

    def root_cause_classified(self, ranked: list[dict[str, Any]], **extra: Any) -> None:
        """Record ranked classification output."""
        self._append(
            "root_cause_classified",
            {"ranked_causes": ranked, **extra},
        )

    def repair_plan_created(self, plan: dict[str, Any], **extra: Any) -> None:
        """Record generated remediation plan payload."""
        self._append("repair_plan_created", {"plan": plan, **extra})

    def repair_started(self, steps: list[str], **extra: Any) -> None:
        """Record start of repair step execution."""
        self._append("repair_started", {"steps": steps, **extra})

    def repair_completed(self, results: list[dict[str, Any]], **extra: Any) -> None:
        """Record completion status of repair execution."""
        self._append("repair_completed", {"results": results, **extra})

    def verification_completed(self, verification: dict[str, Any], **extra: Any) -> None:
        """Record post-repair verification outcome."""
        self._append(
            "verification_completed",
            {"verification": verification, **extra},
        )

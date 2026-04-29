"""Append-only structured JSONL logs for local observability (no secrets)."""

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
    return datetime.now(timezone.utc).isoformat()


class JsonlEventLogger:
    """Writes one JSON object per line with stable event types."""

    def __init__(self, path: Path, run_id: str | None = None) -> None:
        self.path = path
        self.run_id = run_id or str(uuid.uuid4())

    def _append(self, event_type: EventType, payload: dict[str, Any]) -> None:
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
        self._append("diagnosis_started", {"mode": mode, **extra})

    def diagnosis_completed(self, evidence_summary: dict[str, Any], **extra: Any) -> None:
        self._append(
            "diagnosis_completed",
            {"evidence_summary": evidence_summary, **extra},
        )

    def root_cause_classified(self, ranked: list[dict[str, Any]], **extra: Any) -> None:
        self._append(
            "root_cause_classified",
            {"ranked_causes": ranked, **extra},
        )

    def repair_plan_created(self, plan: dict[str, Any], **extra: Any) -> None:
        self._append("repair_plan_created", {"plan": plan, **extra})

    def repair_started(self, steps: list[str], **extra: Any) -> None:
        self._append("repair_started", {"steps": steps, **extra})

    def repair_completed(self, results: list[dict[str, Any]], **extra: Any) -> None:
        self._append("repair_completed", {"results": results, **extra})

    def verification_completed(self, verification: dict[str, Any], **extra: Any) -> None:
        self._append(
            "verification_completed",
            {"verification": verification, **extra},
        )

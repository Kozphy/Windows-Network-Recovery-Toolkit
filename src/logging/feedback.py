"""Structured user feedback for calibration (local JSONL)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .audit import append_jsonl

FeedbackState = Literal["true", "false", "unknown"]


@dataclass(frozen=True)
class FeedbackRecord:
    diagnosis_id: str
    recommended_action: str
    user_feedback_fixed: FeedbackState
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "feedback",
            "feedback_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "diagnosis_id": self.diagnosis_id,
            "recommended_action": self.recommended_action,
            "user_feedback_fixed": self.user_feedback_fixed,
            "notes": self.notes,
        }


def append_feedback(path: Path, record: FeedbackRecord) -> None:
    append_jsonl(path, record.to_dict())

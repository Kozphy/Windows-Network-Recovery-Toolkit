"""Local persistence for DecisionEnvelope by case_id (append-friendly JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.platform_core.decision_context.models import DecisionEnvelope


def _store_root() -> Path:
    raw = os.environ.get("WNT_DECISION_CONTEXT_DIR") or os.environ.get("WNT_AUDIT_DIR", ".audit")
    return Path(raw) / "decision_context"


def _safe_case_filename(case_id: str) -> str:
    """Windows-safe filename from case id (no colon/asterisk path chars)."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in case_id.strip())
    return cleaned[:180] or "case"


def save_decision_envelope(envelope: DecisionEnvelope, *, root: Path | None = None) -> Path:
    base = root or _store_root()
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{_safe_case_filename(envelope.case_id)}.json"
    path.write_text(json.dumps(envelope.to_dict(), indent=2), encoding="utf-8")
    latest = base / "latest.json"
    latest.write_text(
        json.dumps({"case_id": envelope.case_id, "path": str(path)}, indent=2),
        encoding="utf-8",
    )
    return path


def load_decision_envelope(case_id: str, *, root: Path | None = None) -> DecisionEnvelope | None:
    base = root or _store_root()
    path = base / f"{_safe_case_filename(case_id)}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return DecisionEnvelope.model_validate(data)


def load_latest_decision_envelope(*, root: Path | None = None) -> DecisionEnvelope | None:
    base = root or _store_root()
    latest = base / "latest.json"
    if not latest.is_file():
        return None
    meta: dict[str, Any] = json.loads(latest.read_text(encoding="utf-8"))
    case_id = str(meta.get("case_id") or "")
    if not case_id:
        return None
    return load_decision_envelope(case_id, root=base)

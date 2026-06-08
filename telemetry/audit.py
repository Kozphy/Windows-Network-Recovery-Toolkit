"""Append-only audit sink for registry writer evidence fusion (no raw events by default)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from telemetry.models import RegistryWriterEvidence


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def append_registry_writer_evidence_audit(
    evidence: RegistryWriterEvidence | dict[str, Any],
    *,
    proxy_change_time: datetime | str | None = None,
    audit_path: Path | None = None,
    include_raw: bool = False,
) -> Path:
    """Append one fusion summary row to logs/registry_writer_evidence.jsonl."""
    path = audit_path or (
        Path(__file__).resolve().parent.parent / "logs" / "registry_writer_evidence.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(evidence, RegistryWriterEvidence):
        evidence_dict = evidence.to_dict(include_raw=include_raw)
    else:
        evidence_dict = dict(evidence)

    if isinstance(proxy_change_time, datetime):
        change_time = proxy_change_time.isoformat()
    else:
        change_time = proxy_change_time

    row: dict[str, Any] = {
        "timestamp_utc": _now_iso(),
        "proxy_change_time": change_time,
        "evidence_level": evidence_dict.get("evidence_level"),
        "matched_event_count": len(evidence_dict.get("matched_events") or []),
        "candidate_writers": evidence_dict.get("candidate_writers") or [],
        "listener_match": evidence_dict.get("listener_match"),
        "limitations": evidence_dict.get("limitations") or [],
        "recommended_next_steps": evidence_dict.get("recommended_next_steps") or [],
        "confidence_rank": evidence_dict.get("confidence_rank"),
    }
    if include_raw:
        row["matched_events"] = evidence_dict.get("matched_events") or []

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path

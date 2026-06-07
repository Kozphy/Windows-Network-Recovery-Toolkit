"""Append-only JSONL incident store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from platform_core.incident_model import IncidentRecord, IncidentState
from platform_core.models import utc_now_iso
from platform_core.storage import _path, append_jsonl, iter_jsonl


def append_incident_event(row: dict[str, Any], *, store_path: Path | None = None) -> None:
    path = store_path or _path("incidents.jsonl")
    append_jsonl(path, row)


def list_incident_rows(*, store_path: Path | None = None) -> list[dict[str, Any]]:
    path = store_path or _path("incidents.jsonl")
    latest: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(path):
        iid = str(row.get("incident_id") or "")
        if iid:
            latest[iid] = row
    return sorted(latest.values(), key=lambda r: str(r.get("updated_at") or ""))


def get_incident(incident_id: str, *, store_path: Path | None = None) -> dict[str, Any] | None:
    path = store_path or _path("incidents.jsonl")
    latest: dict[str, Any] | None = None
    for row in iter_jsonl(path):
        if str(row.get("incident_id") or "") == incident_id:
            latest = row
    return latest


def transition_incident(
    incident_id: str,
    *,
    new_state: IncidentState,
    actor: str = "platform_api",
    store_path: Path | None = None,
) -> IncidentRecord:
    current = get_incident(incident_id, store_path=store_path)
    if not current:
        raise KeyError(f"incident not found: {incident_id}")
    record = IncidentRecord.model_validate(current)
    row = record.model_dump(mode="json")
    row["state"] = new_state
    row["updated_at"] = utc_now_iso()
    row["last_transition_actor"] = actor
    append_incident_event(row, store_path=store_path)
    return IncidentRecord.model_validate(row)

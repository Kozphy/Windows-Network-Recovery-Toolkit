"""Outcome store — append-only JSONL."""

from __future__ import annotations

import uuid
from pathlib import Path

from platform_core.models import utc_now_iso
from src.platform_core.contracts import IncidentOutcome

_DEFAULT = Path("logs/canonical_outcomes.jsonl")


def record_outcome(
    *,
    decision_id: str,
    incident_id: str,
    recommended_action: str,
    policy_outcome: str,
    operator_action: str = "",
    actual_outcome: str = "",
    time_to_resolution_seconds: float | None = None,
    was_successful: bool | None = None,
    was_false_positive: bool | None = None,
    was_blocked_by_policy: bool = False,
    notes: str = "",
    path: Path | None = None,
) -> IncidentOutcome:
    target = path or _DEFAULT
    target.parent.mkdir(parents=True, exist_ok=True)
    row = IncidentOutcome(
        outcome_id=f"out-{uuid.uuid4().hex[:12]}",
        decision_id=decision_id,
        incident_id=incident_id,
        created_at=utc_now_iso(),
        recommended_action=recommended_action,
        policy_outcome=policy_outcome,
        operator_action=operator_action,
        actual_outcome=actual_outcome,
        time_to_resolution_seconds=time_to_resolution_seconds,
        was_successful=was_successful,
        was_false_positive=was_false_positive,
        was_blocked_by_policy=was_blocked_by_policy,
        notes=notes,
    )
    with target.open("a", encoding="utf-8") as fh:
        fh.write(row.model_dump_json() + "\n")
    return row


def load_outcomes(path: Path | None = None) -> list[IncidentOutcome]:
    target = path or _DEFAULT
    if not target.is_file():
        return []
    rows: list[IncidentOutcome] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(IncidentOutcome.model_validate_json(line))
        except Exception:  # noqa: BLE001
            continue
    return rows

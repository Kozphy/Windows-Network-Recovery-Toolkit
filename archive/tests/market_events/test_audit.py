from __future__ import annotations

import json
from pathlib import Path

from src.market_events.audit import append_market_audit
from src.market_events.calendar import get_event
from src.market_events.scoring import score_event


def test_audit_append(tmp_path: Path, calendar_fixture: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    event = get_event("CPI_2026_06", calendar_fixture)
    score = score_event(event)
    entry = append_market_audit(
        command="score",
        event_id=event.event_id,
        input_payload=event.model_dump(mode="json"),
        output_payload=score.model_dump(mode="json"),
        policy_status=score.policy_status,
        explanation="test audit",
        audit_path=log_path,
    )
    assert log_path.is_file()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_id"] == "CPI_2026_06"
    assert row["command"] == "score"
    assert len(row["input_hash"]) == 64
    assert len(row["output_hash"]) == 64
    assert entry["policy_status"] == score.policy_status.value

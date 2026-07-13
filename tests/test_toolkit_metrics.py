"""Toolkit log metrics rollup."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.event_store import record_live_diagnosis_run
from platform_core.toolkit_metrics import compute_toolkit_metrics


def test_compute_toolkit_metrics_counts(tmp_path: Path) -> None:
    record_live_diagnosis_run(
        tmp_path,
        run_id="m1",
        observations={},
        hypothesis_decisions=[
            {
                "decision": "BLOCK",
                "reason_codes": ["DESTRUCTIVE_ACTION_BLOCKED"],
                "blocked_actions": [],
            }
        ],
    )
    # Synthetic order-flow audit row (order_flow_simulator is archived).
    logs = tmp_path / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "order_flow_audit.jsonl").write_text(
        json.dumps({"valid": False, "latency_ms": 12.5}) + "\n",
        encoding="utf-8",
    )
    m = compute_toolkit_metrics(tmp_path)
    assert m["event_count"] >= 1
    assert m["decision_count"] >= 1
    assert m["invalid_transition_count"] >= 1

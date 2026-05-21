"""Toolkit log metrics rollup."""

from __future__ import annotations

from pathlib import Path

from platform_core.event_store import record_live_diagnosis_run
from platform_core.toolkit_metrics import compute_toolkit_metrics
from order_flow_simulator import OrderFlowSimulator


def test_compute_toolkit_metrics_counts(tmp_path: Path) -> None:
    record_live_diagnosis_run(
        tmp_path,
        run_id="m1",
        observations={},
        hypothesis_decisions=[{"decision": "BLOCK", "reason_codes": ["DESTRUCTIVE_ACTION_BLOCKED"], "blocked_actions": []}],
    )
    OrderFlowSimulator(repo_root=tmp_path).run_scenario("invalid_cancel", order_id="O1")
    m = compute_toolkit_metrics(tmp_path)
    assert m["event_count"] >= 1
    assert m["decision_count"] >= 1
    assert m["invalid_transition_count"] >= 1

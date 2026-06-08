"""Order-flow simulator: FSM, invalid transitions, audit, replay."""

from __future__ import annotations

from pathlib import Path

from order_flow_simulator.models import OrderEventType, OrderState
from order_flow_simulator.simulator import OrderFlowSimulator
from order_flow_simulator.state_machine import apply_event


def test_happy_path_reaches_filled(tmp_path: Path) -> None:
    sim = OrderFlowSimulator(repo_root=tmp_path)
    result = sim.run_scenario("happy_path", order_id="T1")
    assert result.final_state == OrderState.FILLED
    assert result.invalid_transition_count == 0
    assert (tmp_path / "logs" / "order_flow_audit.jsonl").is_file()


def test_invalid_cancel_after_fill_counts_invalid(tmp_path: Path) -> None:
    sim = OrderFlowSimulator(repo_root=tmp_path)
    result = sim.run_scenario("invalid_cancel", order_id="T2")
    assert result.invalid_transition_count >= 1
    assert result.final_state == OrderState.FILLED


def test_replay_reads_audit_without_mutation(tmp_path: Path) -> None:
    sim = OrderFlowSimulator(repo_root=tmp_path)
    sim.run_scenario("cancel_path", order_id="T3")
    rows = sim.replay_order("T3")
    assert len(rows) >= 4
    assert rows[-1]["to_state"] == OrderState.CANCELLED.value


def test_apply_event_rejects_bad_transition() -> None:
    after, valid, _ = apply_event(OrderState.FILLED, OrderEventType.CANCEL_REQUESTED)
    assert not valid
    assert after == OrderState.FILLED

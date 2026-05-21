"""Run scripted order scenarios with latency metrics and JSONL audit."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from order_flow_simulator.models import OrderEventType, OrderState
from order_flow_simulator.state_machine import apply_event, build_audit_event

AUDIT_REL = "logs/order_flow_audit.jsonl"

SCENARIOS: dict[str, list[OrderEventType]] = {
    "happy_path": [
        OrderEventType.ORDER_SUBMITTED,
        OrderEventType.ORDER_ACCEPTED,
        OrderEventType.PARTIAL_FILL,
        OrderEventType.FULL_FILL,
    ],
    "cancel_path": [
        OrderEventType.ORDER_SUBMITTED,
        OrderEventType.ORDER_ACCEPTED,
        OrderEventType.CANCEL_REQUESTED,
        OrderEventType.CANCEL_CONFIRMED,
    ],
    "invalid_cancel": [
        OrderEventType.ORDER_SUBMITTED,
        OrderEventType.ORDER_ACCEPTED,
        OrderEventType.FULL_FILL,
        OrderEventType.CANCEL_REQUESTED,
    ],
    "reject_early": [
        OrderEventType.ORDER_SUBMITTED,
        OrderEventType.REJECT,
    ],
}


@dataclass
class SimulationResult:
    """Outcome of one scenario run."""

    scenario: str
    order_id: str
    final_state: OrderState
    events: list[dict[str, Any]] = field(default_factory=list)
    invalid_transition_count: int = 0
    processing_latency_ms_total: float = 0.0
    audit_path: str = ""

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "order_id": self.order_id,
            "final_state": self.final_state.value,
            "invalid_transition_count": self.invalid_transition_count,
            "processing_latency_ms_total": round(self.processing_latency_ms_total, 3),
            "audit_path": self.audit_path,
            "events": self.events,
        }


class OrderFlowSimulator:
    """In-memory FSM with append-only audit."""

    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self._states: dict[str, OrderState] = {}

    def _state(self, order_id: str) -> OrderState:
        return self._states.get(order_id, OrderState.NEW)

    def apply(
        self,
        order_id: str,
        event_type: OrderEventType,
        *,
        simulated_latency_ms: float = 0.05,
    ) -> dict[str, Any]:
        """Apply one event; append audit line; return event JSON."""
        t0 = time.perf_counter()
        before = self._state(order_id)
        after, valid, detail = apply_event(before, event_type)
        if order_id not in self._states and event_type == OrderEventType.ORDER_SUBMITTED:
            self._states[order_id] = OrderState.NEW
            before = OrderState.NEW
            after, valid, detail = apply_event(before, event_type)
        if valid:
            self._states[order_id] = after
        elapsed_ms = (time.perf_counter() - t0) * 1000.0 + simulated_latency_ms
        row = build_audit_event(
            order_id=order_id,
            event_type=event_type,
            from_state=before,
            to_state=after if valid else before,
            valid=valid,
            latency_ms=elapsed_ms,
            detail=detail,
        )
        blob = row.to_jsonable()
        path = self.repo_root / AUDIT_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(blob, ensure_ascii=False) + "\n")
        return blob

    def run_scenario(self, name: str, *, order_id: str | None = None) -> SimulationResult:
        """Execute a named scenario script."""
        script = SCENARIOS.get(name)
        if script is None:
            raise ValueError(f"unknown scenario: {name!r}; choose from {sorted(SCENARIOS)}")
        oid = order_id or f"ORD-{name}"
        self._states[oid] = OrderState.NEW
        invalid = 0
        total_ms = 0.0
        events: list[dict[str, Any]] = []
        for et in script:
            blob = self.apply(oid, et)
            events.append(blob)
            total_ms += float(blob.get("latency_ms") or 0)
            if not blob.get("valid"):
                invalid += 1
        return SimulationResult(
            scenario=name,
            order_id=oid,
            final_state=self._state(oid),
            events=events,
            invalid_transition_count=invalid,
            processing_latency_ms_total=total_ms,
            audit_path=str(self.repo_root / AUDIT_REL),
        )

    def replay_order(self, order_id: str) -> list[dict[str, Any]]:
        """Load audit rows for one order (read-only)."""
        path = self.repo_root / AUDIT_REL
        if not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("order_id") == order_id:
                out.append(row)
        return out

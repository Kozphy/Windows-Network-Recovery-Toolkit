"""Order-flow event and state models for the portfolio state-machine simulator.

Module responsibility:
    Define :class:`OrderState`, :class:`OrderEventType`, and :class:`OrderEvent` JSON
    shapes appended to ``logs/order_flow_audit.jsonl``.

System placement:
    Used by :mod:`order_flow_simulator.state_machine` and :mod:`simulator`; independent
    of Windows proxy/network remediation.

Data shape:
    Audit rows include ``schema_version=order_flow.v1``, ``record_type=order_flow_event``,
    ``latency_ms``, ``valid``, and stringified state transitions.

Timezone:
    ``OrderEvent.timestamp`` defaults to UTC ISO-8601 via :func:`platform_core.models.utc_now_iso`.

Output guarantees:
    :meth:`OrderEvent.to_jsonable` returns JSON-serializable dicts with rounded latency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from platform_core.models import utc_now_iso


class OrderState(StrEnum):
    """Order lifecycle states."""

    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderEventType(StrEnum):
    """Inbound event types (exchange-style vocabulary)."""

    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACCEPTED = "order_accepted"
    PARTIAL_FILL = "partial_fill"
    FULL_FILL = "full_fill"
    CANCEL_REQUESTED = "cancel_requested"
    CANCEL_CONFIRMED = "cancel_confirmed"
    REJECT = "reject"


@dataclass(frozen=True)
class OrderEvent:
    """Single append-only audit event."""

    event_type: OrderEventType
    order_id: str
    timestamp: str = field(default_factory=utc_now_iso)
    latency_ms: float = 0.0
    from_state: OrderState | None = None
    to_state: OrderState | None = None
    valid: bool = True
    detail: str = ""

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "schema_version": "order_flow.v1",
            "record_type": "order_flow_event",
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "order_id": self.order_id,
            "latency_ms": round(self.latency_ms, 3),
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value if self.to_state else None,
            "valid": self.valid,
            "detail": self.detail,
        }

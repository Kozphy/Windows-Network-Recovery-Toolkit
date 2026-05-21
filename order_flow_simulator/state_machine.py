"""Valid order state transitions and event application."""

from __future__ import annotations

from order_flow_simulator.models import OrderEvent, OrderEventType, OrderState

# event -> (required_from_states, to_state)
_EVENT_RULES: dict[OrderEventType, tuple[frozenset[OrderState], OrderState]] = {
    OrderEventType.ORDER_SUBMITTED: (frozenset({OrderState.NEW}), OrderState.NEW),
    OrderEventType.ORDER_ACCEPTED: (frozenset({OrderState.NEW}), OrderState.ACCEPTED),
    OrderEventType.PARTIAL_FILL: (
        frozenset({OrderState.ACCEPTED, OrderState.PARTIALLY_FILLED}),
        OrderState.PARTIALLY_FILLED,
    ),
    OrderEventType.FULL_FILL: (
        frozenset({OrderState.ACCEPTED, OrderState.PARTIALLY_FILLED}),
        OrderState.FILLED,
    ),
    OrderEventType.CANCEL_REQUESTED: (
        frozenset({OrderState.ACCEPTED, OrderState.PARTIALLY_FILLED}),
        OrderState.CANCEL_PENDING,
    ),
    OrderEventType.CANCEL_CONFIRMED: (frozenset({OrderState.CANCEL_PENDING}), OrderState.CANCELLED),
    OrderEventType.REJECT: (frozenset({OrderState.NEW, OrderState.ACCEPTED}), OrderState.REJECTED),
}


def apply_event(current: OrderState, event_type: OrderEventType) -> tuple[OrderState, bool, str]:
    """Return (new_state, valid, detail)."""
    rule = _EVENT_RULES.get(event_type)
    if rule is None:
        return current, False, f"unknown_event_type:{event_type.value}"
    allowed_from, to_state = rule
    if current not in allowed_from:
        return (
            current,
            False,
            f"invalid_transition:{current.value}->{to_state.value} via {event_type.value}",
        )
    return to_state, True, "ok"


def build_audit_event(
    *,
    order_id: str,
    event_type: OrderEventType,
    from_state: OrderState,
    to_state: OrderState,
    valid: bool,
    latency_ms: float,
    detail: str,
) -> OrderEvent:
    """Materialize an audit row for append-only logs."""
    return OrderEvent(
        event_type=event_type,
        order_id=order_id,
        from_state=from_state,
        to_state=to_state,
        valid=valid,
        latency_ms=latency_ms,
        detail=detail,
    )

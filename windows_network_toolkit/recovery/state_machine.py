"""Audited finite-state machine for network recovery workflows.

The state machine is intentionally dependency-free and does not perform monitoring,
remediation, or persistence itself. Callers drive transitions and may provide an
``on_transition`` callback to append records to the existing audit/event store.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Any


class RecoveryState(StrEnum):
    """Lifecycle states for a monitored recovery incident."""

    INITIALIZING = "initializing"
    MONITORING = "monitoring"
    HEALTHY = "healthy"
    DRIFT_DETECTED = "drift_detected"
    DIAGNOSING = "diagnosing"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    RECOVERED = "recovered"
    ESCALATED = "escalated"
    FAILED = "failed"


ALLOWED_TRANSITIONS: Mapping[RecoveryState, frozenset[RecoveryState]] = {
    RecoveryState.INITIALIZING: frozenset(
        {RecoveryState.MONITORING, RecoveryState.FAILED}
    ),
    RecoveryState.MONITORING: frozenset(
        {RecoveryState.HEALTHY, RecoveryState.DRIFT_DETECTED, RecoveryState.FAILED}
    ),
    RecoveryState.HEALTHY: frozenset(
        {RecoveryState.MONITORING, RecoveryState.DRIFT_DETECTED}
    ),
    RecoveryState.DRIFT_DETECTED: frozenset(
        {RecoveryState.DIAGNOSING, RecoveryState.ESCALATED, RecoveryState.FAILED}
    ),
    RecoveryState.DIAGNOSING: frozenset(
        {RecoveryState.REMEDIATING, RecoveryState.VERIFYING, RecoveryState.ESCALATED}
    ),
    RecoveryState.REMEDIATING: frozenset(
        {RecoveryState.VERIFYING, RecoveryState.ESCALATED, RecoveryState.FAILED}
    ),
    RecoveryState.VERIFYING: frozenset(
        {
            RecoveryState.RECOVERED,
            RecoveryState.DIAGNOSING,
            RecoveryState.ESCALATED,
            RecoveryState.FAILED,
        }
    ),
    RecoveryState.RECOVERED: frozenset(
        {RecoveryState.MONITORING, RecoveryState.DRIFT_DETECTED}
    ),
    RecoveryState.ESCALATED: frozenset(
        {RecoveryState.REMEDIATING, RecoveryState.VERIFYING, RecoveryState.FAILED}
    ),
    RecoveryState.FAILED: frozenset(),
}


class InvalidStateTransition(ValueError):
    """Raised when a caller requests a transition not allowed by policy."""

    def __init__(self, previous_state: RecoveryState, new_state: RecoveryState) -> None:
        self.previous_state = previous_state
        self.new_state = new_state
        super().__init__(
            f"Illegal recovery transition: {previous_state.value} -> {new_state.value}"
        )


@dataclass(frozen=True, slots=True)
class StateTransition:
    """Immutable audit record for one accepted state transition."""

    previous_state: RecoveryState
    new_state: RecoveryState
    timestamp: str
    trigger: str
    reason: str
    correlation_id: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    actor: str = "automatic"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable transition representation."""

        result = asdict(self)
        result["previous_state"] = self.previous_state.value
        result["new_state"] = self.new_state.value
        result["evidence"] = dict(self.evidence)
        return result


TransitionCallback = Callable[[StateTransition], None]


class RecoveryStateMachine:
    """Thread-safe finite-state machine with immutable transition history."""

    def __init__(
        self,
        *,
        correlation_id: str,
        initial_state: RecoveryState = RecoveryState.INITIALIZING,
        on_transition: TransitionCallback | None = None,
    ) -> None:
        if not correlation_id.strip():
            raise ValueError("correlation_id must not be empty")

        self._correlation_id = correlation_id
        self._state = initial_state
        self._on_transition = on_transition
        self._history: list[StateTransition] = []
        self._lock = RLock()

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    @property
    def state(self) -> RecoveryState:
        with self._lock:
            return self._state

    @property
    def history(self) -> tuple[StateTransition, ...]:
        with self._lock:
            return tuple(self._history)

    def can_transition_to(self, new_state: RecoveryState) -> bool:
        """Return whether ``new_state`` is currently permitted."""

        with self._lock:
            return new_state in ALLOWED_TRANSITIONS[self._state]

    def transition(
        self,
        new_state: RecoveryState,
        *,
        trigger: str,
        reason: str,
        evidence: Mapping[str, Any] | None = None,
        actor: str = "automatic",
        timestamp: str | None = None,
    ) -> StateTransition:
        """Validate, record, publish, and return one transition.

        The callback runs after the in-memory state and history are updated. If the
        callback fails, the accepted transition remains recorded and the callback
        exception is propagated so the caller can handle audit persistence failure.
        """

        if not trigger.strip():
            raise ValueError("trigger must not be empty")
        if not reason.strip():
            raise ValueError("reason must not be empty")
        if not actor.strip():
            raise ValueError("actor must not be empty")

        with self._lock:
            previous_state = self._state
            if new_state not in ALLOWED_TRANSITIONS[previous_state]:
                raise InvalidStateTransition(previous_state, new_state)

            record = StateTransition(
                previous_state=previous_state,
                new_state=new_state,
                timestamp=timestamp or datetime.now(UTC).isoformat(),
                trigger=trigger,
                reason=reason,
                correlation_id=self._correlation_id,
                evidence=dict(evidence or {}),
                actor=actor,
            )
            self._state = new_state
            self._history.append(record)

        if self._on_transition is not None:
            self._on_transition(record)

        return record

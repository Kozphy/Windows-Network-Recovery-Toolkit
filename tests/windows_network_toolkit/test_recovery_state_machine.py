from __future__ import annotations

import pytest

from windows_network_toolkit.recovery import (
    InvalidStateTransition,
    RecoveryState,
    RecoveryStateMachine,
)


def test_successful_recovery_flow_records_audit_history() -> None:
    published = []
    machine = RecoveryStateMachine(
        correlation_id="inc-123",
        on_transition=published.append,
    )

    flow = [
        (RecoveryState.MONITORING, "startup_complete"),
        (RecoveryState.DRIFT_DETECTED, "proxy_changed"),
        (RecoveryState.DIAGNOSING, "diagnosis_started"),
        (RecoveryState.REMEDIATING, "policy_approved"),
        (RecoveryState.VERIFYING, "remediation_complete"),
        (RecoveryState.RECOVERED, "health_check_passed"),
        (RecoveryState.MONITORING, "monitoring_resumed"),
    ]

    for state, trigger in flow:
        machine.transition(
            state,
            trigger=trigger,
            reason=f"Transition requested by {trigger}",
            evidence={"source": "test"},
        )

    assert machine.state is RecoveryState.MONITORING
    assert len(machine.history) == len(flow)
    assert published == list(machine.history)
    assert machine.history[0].previous_state is RecoveryState.INITIALIZING
    assert machine.history[-1].new_state is RecoveryState.MONITORING
    assert machine.history[-1].correlation_id == "inc-123"


def test_invalid_transition_is_rejected_without_mutating_state() -> None:
    machine = RecoveryStateMachine(correlation_id="inc-invalid")

    with pytest.raises(InvalidStateTransition) as exc_info:
        machine.transition(
            RecoveryState.REMEDIATING,
            trigger="skip_diagnosis",
            reason="Invalid direct remediation attempt",
        )

    assert machine.state is RecoveryState.INITIALIZING
    assert machine.history == ()
    assert exc_info.value.previous_state is RecoveryState.INITIALIZING
    assert exc_info.value.new_state is RecoveryState.REMEDIATING


def test_verification_failure_can_retry_diagnosis() -> None:
    machine = RecoveryStateMachine(correlation_id="inc-retry")
    for state in (
        RecoveryState.MONITORING,
        RecoveryState.DRIFT_DETECTED,
        RecoveryState.DIAGNOSING,
        RecoveryState.REMEDIATING,
        RecoveryState.VERIFYING,
        RecoveryState.DIAGNOSING,
    ):
        machine.transition(
            state,
            trigger=f"enter_{state.value}",
            reason="Exercise retry path",
        )

    assert machine.state is RecoveryState.DIAGNOSING
    assert machine.history[-1].previous_state is RecoveryState.VERIFYING


def test_escalation_can_end_in_failed_terminal_state() -> None:
    machine = RecoveryStateMachine(correlation_id="inc-failed")
    for state in (
        RecoveryState.MONITORING,
        RecoveryState.DRIFT_DETECTED,
        RecoveryState.ESCALATED,
        RecoveryState.FAILED,
    ):
        machine.transition(
            state,
            trigger=f"enter_{state.value}",
            reason="Exercise escalation path",
        )

    assert machine.state is RecoveryState.FAILED
    assert not machine.can_transition_to(RecoveryState.MONITORING)


def test_transition_record_is_json_serializable_shape() -> None:
    machine = RecoveryStateMachine(correlation_id="inc-json")
    record = machine.transition(
        RecoveryState.MONITORING,
        trigger="service_started",
        reason="Watcher initialized",
        evidence={"component": "proxy_watcher"},
        actor="system",
        timestamp="2026-08-05T00:00:00+00:00",
    )

    assert record.to_dict() == {
        "previous_state": "initializing",
        "new_state": "monitoring",
        "timestamp": "2026-08-05T00:00:00+00:00",
        "trigger": "service_started",
        "reason": "Watcher initialized",
        "correlation_id": "inc-json",
        "evidence": {"component": "proxy_watcher"},
        "actor": "system",
    }


@pytest.mark.parametrize("field", ["trigger", "reason", "actor"])
def test_required_transition_metadata_cannot_be_blank(field: str) -> None:
    machine = RecoveryStateMachine(correlation_id="inc-metadata")
    kwargs = {
        "trigger": "service_started",
        "reason": "Watcher initialized",
        "actor": "system",
    }
    kwargs[field] = " "

    with pytest.raises(ValueError):
        machine.transition(RecoveryState.MONITORING, **kwargs)


def test_correlation_id_cannot_be_blank() -> None:
    with pytest.raises(ValueError):
        RecoveryStateMachine(correlation_id=" ")

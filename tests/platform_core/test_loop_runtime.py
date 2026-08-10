from src.platform_core.agents.loop_runtime import (
    AgentLoopRuntime,
    GraphNode,
    LoopState,
    LoopStatus,
    StepResult,
    build_incident_response_graph,
)


def test_incident_loop_recovers_after_reverification():
    calls = {"verify": 0}

    def observe(state):
        return StepResult("evidence_ready", {"evidence": True})

    def diagnose(state):
        return StepResult("actionable", {"diagnosis": "dead_proxy"})

    def remediate(state):
        return StepResult("applied", {"repair_applied": True})

    def verify(state):
        calls["verify"] += 1
        if calls["verify"] == 1:
            return StepResult("still_broken", reason="first verification failed")
        return StepResult("recovered", reason="connectivity restored")

    runtime = build_incident_response_graph(
        observe=observe,
        diagnose=diagnose,
        remediate=remediate,
        verify=verify,
    )
    state = runtime.run(LoopState(current_node="observe"))

    assert state.status is LoopStatus.SUCCEEDED
    assert state.terminal_reason == "connectivity restored"
    assert [event["node"] for event in state.history] == [
        "observe",
        "diagnose",
        "remediate",
        "verify",
        "diagnose",
        "remediate",
        "verify",
    ]
    assert state.checkpoints


def test_retry_budget_escalates_to_human_review():
    def retry(_state):
        return StepResult("retry", reason="tool remained unavailable")

    runtime = AgentLoopRuntime(
        {
            "tool": GraphNode(
                name="tool",
                handler=retry,
                routes={},
                max_attempts=2,
            )
        }
    )
    state = runtime.run(LoopState(current_node="tool"))

    assert state.status is LoopStatus.NEEDS_HUMAN_REVIEW
    assert state.attempts["tool"] == 2
    assert state.terminal_reason == "tool remained unavailable"


def test_unhandled_outcome_fails_closed_to_review():
    runtime = AgentLoopRuntime(
        {
            "router": GraphNode(
                name="router",
                handler=lambda _state: StepResult("unexpected"),
                routes={"known": "__success__"},
            )
        }
    )
    state = runtime.run(LoopState(current_node="router"))

    assert state.status is LoopStatus.NEEDS_HUMAN_REVIEW
    assert "unhandled outcome" in (state.terminal_reason or "")

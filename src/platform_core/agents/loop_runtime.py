"""Stateful graph runtime for bounded agent loops.

The runtime is deterministic and framework-free. It provides explicit state,
conditional routing, retry budgets, checkpoints, and human-review escalation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class LoopStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


@dataclass(frozen=True)
class StepResult:
    outcome: str
    updates: Mapping[str, Any] = field(default_factory=dict)
    reason: str | None = None


@dataclass
class LoopState:
    current_node: str
    context: dict[str, Any] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    status: LoopStatus = LoopStatus.RUNNING
    terminal_reason: str | None = None

    def checkpoint(self) -> None:
        self.checkpoints.append(
            {
                "current_node": self.current_node,
                "context": dict(self.context),
                "attempts": dict(self.attempts),
                "history_length": len(self.history),
                "status": self.status.value,
            }
        )


NodeHandler = Callable[[LoopState], StepResult]


@dataclass(frozen=True)
class GraphNode:
    name: str
    handler: NodeHandler
    routes: Mapping[str, str] = field(default_factory=dict)
    max_attempts: int = 1
    retry_outcomes: frozenset[str] = frozenset({"retry"})


class AgentLoopRuntime:
    """Execute a bounded state graph with deterministic routing."""

    TERMINAL_ROUTES = {
        "__success__": LoopStatus.SUCCEEDED,
        "__failure__": LoopStatus.FAILED,
        "__human_review__": LoopStatus.NEEDS_HUMAN_REVIEW,
    }

    def __init__(self, nodes: Mapping[str, GraphNode], *, max_steps: int = 32) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.nodes = dict(nodes)
        self.max_steps = max_steps
        self._validate_graph()

    def _validate_graph(self) -> None:
        if not self.nodes:
            raise ValueError("graph must contain at least one node")
        for key, node in self.nodes.items():
            if key != node.name:
                raise ValueError(f"node key {key!r} does not match node.name {node.name!r}")
            if node.max_attempts < 1:
                raise ValueError(f"node {node.name!r} max_attempts must be at least 1")
            for target in node.routes.values():
                if target not in self.nodes and target not in self.TERMINAL_ROUTES:
                    raise ValueError(f"node {node.name!r} routes to unknown target {target!r}")

    def run(self, state: LoopState) -> LoopState:
        if state.current_node not in self.nodes:
            raise ValueError(f"unknown start node {state.current_node!r}")

        for _ in range(self.max_steps):
            if state.status is not LoopStatus.RUNNING:
                return state

            node = self.nodes[state.current_node]
            attempt = state.attempts.get(node.name, 0) + 1
            state.attempts[node.name] = attempt
            state.checkpoint()

            result = node.handler(state)
            state.context.update(result.updates)
            state.history.append(
                {
                    "node": node.name,
                    "attempt": attempt,
                    "outcome": result.outcome,
                    "reason": result.reason,
                }
            )

            if result.outcome in node.retry_outcomes:
                if attempt < node.max_attempts:
                    continue
                state.status = LoopStatus.NEEDS_HUMAN_REVIEW
                state.terminal_reason = result.reason or f"retry budget exhausted at {node.name}"
                return state

            target = node.routes.get(result.outcome)
            if target is None:
                state.status = LoopStatus.NEEDS_HUMAN_REVIEW
                state.terminal_reason = f"unhandled outcome {result.outcome!r} at {node.name}"
                return state

            terminal = self.TERMINAL_ROUTES.get(target)
            if terminal is not None:
                state.status = terminal
                state.terminal_reason = result.reason
                return state

            state.current_node = target

        state.status = LoopStatus.NEEDS_HUMAN_REVIEW
        state.terminal_reason = f"global step budget exhausted ({self.max_steps})"
        return state


def build_incident_response_graph(
    *,
    observe: NodeHandler,
    diagnose: NodeHandler,
    remediate: NodeHandler,
    verify: NodeHandler,
) -> AgentLoopRuntime:
    """Create an observe → diagnose → remediate → verify recovery loop."""

    nodes = {
        "observe": GraphNode(
            name="observe",
            handler=observe,
            routes={"evidence_ready": "diagnose", "insufficient": "__human_review__"},
        ),
        "diagnose": GraphNode(
            name="diagnose",
            handler=diagnose,
            routes={"actionable": "remediate", "safe": "__success__", "uncertain": "__human_review__"},
        ),
        "remediate": GraphNode(
            name="remediate",
            handler=remediate,
            routes={"applied": "verify", "blocked": "__human_review__", "failed": "__failure__"},
            max_attempts=2,
        ),
        "verify": GraphNode(
            name="verify",
            handler=verify,
            routes={"recovered": "__success__", "still_broken": "diagnose", "unsafe": "__human_review__"},
            max_attempts=2,
        ),
    }
    return AgentLoopRuntime(nodes, max_steps=12)

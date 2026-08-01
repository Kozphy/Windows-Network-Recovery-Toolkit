"""Policy-gated execution boundary for agent-proposed tool calls.

The runtime is intentionally model-agnostic. An agent may propose a typed tool
call, but it cannot grant itself execution authority. The registry validates
inputs, policy decides whether the call is allowed, approvals are bound to the
exact proposal hash, and every outcome is returned as a structured record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Callable, Mapping


class PolicyOutcome(StrEnum):
    ALLOW = "ALLOW"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class RunStatus(StrEnum):
    EXECUTED = "EXECUTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"
    FAILED = "FAILED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    allowed_arguments: frozenset[str]
    privileged: bool = False


@dataclass(frozen=True)
class ToolProposal:
    tool_name: str
    arguments: Mapping[str, Any]
    requested_by: str = "agent"

    @property
    def proposal_hash(self) -> str:
        payload = {
            "arguments": dict(self.arguments),
            "requested_by": self.requested_by,
            "tool_name": self.tool_name,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Approval:
    approval_id: str
    proposal_hash: str
    approved_by: str


@dataclass(frozen=True)
class RunRecord:
    status: RunStatus
    proposal_hash: str
    tool_name: str
    policy_outcome: PolicyOutcome
    reason: str
    result: Mapping[str, Any] | None = None


@dataclass
class ExecutionBudget:
    max_total_calls: int = 8
    max_repeated_calls: int = 2
    total_calls: int = 0
    calls_by_hash: dict[str, int] = field(default_factory=dict)

    def consume(self, proposal_hash: str) -> bool:
        repeated = self.calls_by_hash.get(proposal_hash, 0)
        if self.total_calls >= self.max_total_calls:
            return False
        if repeated >= self.max_repeated_calls:
            return False
        self.total_calls += 1
        self.calls_by_hash[proposal_hash] = repeated + 1
        return True


PolicyEvaluator = Callable[[ToolProposal, ToolDefinition], PolicyOutcome]


class GovernedToolRuntime:
    """Canonical validation, policy, approval, budget, and execution boundary."""

    def __init__(
        self,
        tools: Mapping[str, ToolDefinition],
        policy_evaluator: PolicyEvaluator,
        *,
        budget: ExecutionBudget | None = None,
    ) -> None:
        self._tools = dict(tools)
        self._policy_evaluator = policy_evaluator
        self._budget = budget or ExecutionBudget()

    def run(
        self,
        proposal: ToolProposal,
        *,
        approval: Approval | None = None,
    ) -> RunRecord:
        definition = self._tools.get(proposal.tool_name)
        if definition is None:
            return self._record(
                proposal,
                RunStatus.INVALID,
                PolicyOutcome.BLOCK,
                "unknown tool; runtime fails closed",
            )

        unknown_arguments = set(proposal.arguments) - set(definition.allowed_arguments)
        if unknown_arguments:
            return self._record(
                proposal,
                RunStatus.INVALID,
                PolicyOutcome.BLOCK,
                f"unsupported arguments: {sorted(unknown_arguments)}",
            )

        outcome = self._policy_evaluator(proposal, definition)
        if outcome is PolicyOutcome.BLOCK:
            return self._record(
                proposal,
                RunStatus.BLOCKED,
                outcome,
                "policy blocked execution",
            )

        requires_approval = definition.privileged or outcome is PolicyOutcome.HUMAN_REVIEW_REQUIRED
        if requires_approval:
            if approval is None:
                return self._record(
                    proposal,
                    RunStatus.REVIEW_REQUIRED,
                    PolicyOutcome.HUMAN_REVIEW_REQUIRED,
                    "human approval is required",
                )
            if approval.proposal_hash != proposal.proposal_hash:
                return self._record(
                    proposal,
                    RunStatus.BLOCKED,
                    PolicyOutcome.BLOCK,
                    "approval is stale or bound to different proposal material",
                )

        if not self._budget.consume(proposal.proposal_hash):
            return self._record(
                proposal,
                RunStatus.BUDGET_EXHAUSTED,
                PolicyOutcome.BLOCK,
                "tool-call budget exhausted",
            )

        try:
            result = dict(definition.handler(proposal.arguments))
        except Exception as exc:  # boundary converts handler failure to data
            return self._record(
                proposal,
                RunStatus.FAILED,
                outcome,
                f"handler failed: {type(exc).__name__}",
            )

        return self._record(
            proposal,
            RunStatus.EXECUTED,
            outcome,
            "execution completed through governed boundary",
            result=result,
        )

    @staticmethod
    def _record(
        proposal: ToolProposal,
        status: RunStatus,
        outcome: PolicyOutcome,
        reason: str,
        *,
        result: Mapping[str, Any] | None = None,
    ) -> RunRecord:
        return RunRecord(
            status=status,
            proposal_hash=proposal.proposal_hash,
            tool_name=proposal.tool_name,
            policy_outcome=outcome,
            reason=reason,
            result=result,
        )

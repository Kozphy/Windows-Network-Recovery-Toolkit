"""Governed execution loop for RiskClaw tool calls.

The runtime deliberately keeps model planning separate from deterministic execution.
A planner may propose a tool call, but this module validates the tool, applies the
skill-scoped policy, enforces call budgets, and requires explicit approval before
approval-gated handlers can run.
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from riskclaw.policy import ToolPolicyEngine
from riskclaw.schemas import SkillDefinition, ToolDecision, ToolPolicyResult
from riskclaw.tools import ToolNotFoundError, ToolRegistry


class RuntimeStatus(StrEnum):
    COMPLETED = "completed"
    PREVIEWED = "previewed"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"
    FAILED = "failed"


class ToolCallRequest(BaseModel):
    """Planner-proposed tool call; unknown fields fail closed."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    canonical_outcome: str | None = None
    approval_id: UUID | None = None


class ToolExecutionRecord(BaseModel):
    """Audit-ready record for one policy-evaluated tool proposal."""

    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    tool_name: str
    status: RuntimeStatus
    policy: ToolPolicyResult
    validated_input: dict[str, Any] | None = None
    output: Any | None = None
    error: str | None = None


class AgentRunResult(BaseModel):
    """Structured outcome suitable for API, audit, replay, and evaluation."""

    model_config = ConfigDict(extra="forbid")

    status: RuntimeStatus
    records: list[ToolExecutionRecord]
    stop_reason: str
    tool_call_count: int = Field(ge=0)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "LLM proposals do not override deterministic policy decisions.",
            "Tool permission is not execution authority for approval-gated actions.",
        ]
    )


class GovernedToolRunner:
    """Execute validated tool proposals under deny-by-default controls.

    This class is intentionally model-agnostic. OpenAI Agents SDK, LangGraph, MCP,
    or another planner can produce ``ToolCallRequest`` values, while this runtime
    remains the deterministic enforcement boundary.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        skill: SkillDefinition,
        policy_engine: ToolPolicyEngine | None = None,
        max_tool_calls: int = 12,
        max_repeated_calls_per_tool: int = 3,
        approved_ids: set[UUID] | None = None,
    ) -> None:
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1")
        if max_repeated_calls_per_tool < 1:
            raise ValueError("max_repeated_calls_per_tool must be at least 1")

        self.registry = registry
        self.skill = skill
        self.policy_engine = policy_engine or ToolPolicyEngine()
        self.max_tool_calls = max_tool_calls
        self.max_repeated_calls_per_tool = max_repeated_calls_per_tool
        self.approved_ids = approved_ids or set()

    def run(self, requests: list[ToolCallRequest]) -> AgentRunResult:
        records: list[ToolExecutionRecord] = []
        call_counts: Counter[str] = Counter()

        for sequence, request in enumerate(requests, start=1):
            if sequence > self.max_tool_calls:
                return AgentRunResult(
                    status=RuntimeStatus.BLOCKED,
                    records=records,
                    stop_reason="max_tool_call_budget_exceeded",
                    tool_call_count=len(records),
                )

            call_counts[request.tool_name] += 1
            if call_counts[request.tool_name] > self.max_repeated_calls_per_tool:
                return AgentRunResult(
                    status=RuntimeStatus.BLOCKED,
                    records=records,
                    stop_reason=f"repeated_tool_call_limit_exceeded:{request.tool_name}",
                    tool_call_count=len(records),
                )

            try:
                registered = self.registry.get(request.tool_name)
            except ToolNotFoundError:
                policy = ToolPolicyResult(
                    tool_name=request.tool_name,
                    skill_name=self.skill.name,
                    decision=ToolDecision.BLOCK,
                    reasons=["tool_not_registered"],
                )
                records.append(
                    ToolExecutionRecord(
                        sequence=sequence,
                        tool_name=request.tool_name,
                        status=RuntimeStatus.BLOCKED,
                        policy=policy,
                        error="tool_not_registered",
                    )
                )
                return self._finish(records, RuntimeStatus.BLOCKED, "tool_not_registered")

            policy = self.policy_engine.evaluate(
                tool=registered.definition,
                skill=self.skill,
                canonical_outcome=request.canonical_outcome,
            )

            if policy.decision is ToolDecision.BLOCK:
                records.append(
                    ToolExecutionRecord(
                        sequence=sequence,
                        tool_name=request.tool_name,
                        status=RuntimeStatus.BLOCKED,
                        policy=policy,
                        error="policy_blocked",
                    )
                )
                return self._finish(records, RuntimeStatus.BLOCKED, "policy_blocked")

            if policy.decision is ToolDecision.REQUIRE_APPROVAL:
                if request.approval_id is None or request.approval_id not in self.approved_ids:
                    records.append(
                        ToolExecutionRecord(
                            sequence=sequence,
                            tool_name=request.tool_name,
                            status=RuntimeStatus.APPROVAL_REQUIRED,
                            policy=policy,
                            error="valid_approval_required",
                        )
                    )
                    return self._finish(
                        records,
                        RuntimeStatus.APPROVAL_REQUIRED,
                        "valid_approval_required",
                    )

            try:
                validated = self.registry.validate_input(request.tool_name, request.arguments)
                output = registered.handler(validated)
            except Exception as exc:  # enforcement boundary: convert failures to data
                records.append(
                    ToolExecutionRecord(
                        sequence=sequence,
                        tool_name=request.tool_name,
                        status=RuntimeStatus.FAILED,
                        policy=policy,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                return self._finish(records, RuntimeStatus.FAILED, "tool_execution_failed")

            status = (
                RuntimeStatus.PREVIEWED
                if policy.decision is ToolDecision.PREVIEW
                else RuntimeStatus.COMPLETED
            )
            records.append(
                ToolExecutionRecord(
                    sequence=sequence,
                    tool_name=request.tool_name,
                    status=status,
                    policy=policy,
                    validated_input=validated.model_dump(mode="json"),
                    output=output,
                )
            )

        return self._finish(records, RuntimeStatus.COMPLETED, "all_tool_calls_completed")

    @staticmethod
    def _finish(
        records: list[ToolExecutionRecord],
        status: RuntimeStatus,
        stop_reason: str,
    ) -> AgentRunResult:
        return AgentRunResult(
            status=status,
            records=records,
            stop_reason=stop_reason,
            tool_call_count=len(records),
        )

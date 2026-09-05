from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from riskclaw.runtime import GovernedToolRunner, RuntimeStatus, ToolCallRequest
from riskclaw.schemas import SkillDefinition, SkillRiskLevel, ToolDefinition, ToolRiskClass
from riskclaw.tools import ToolRegistry


class EchoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def _registry(risk_class: ToolRiskClass = ToolRiskClass.READ_ONLY) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo",
            description="Return validated input for deterministic runtime tests.",
            risk_class=risk_class,
        ),
        input_model=EchoInput,
        handler=lambda payload: {"value": payload.value},
    )
    return registry


def _skill(
    *,
    risk_level: SkillRiskLevel = SkillRiskLevel.READ_ONLY,
    requires_human_approval: bool = False,
) -> SkillDefinition:
    return SkillDefinition(
        name="investigate",
        description="Fixture-first investigation skill.",
        allowed_tools=["echo"],
        risk_level=risk_level,
        requires_human_approval=requires_human_approval,
        instructions="Use deterministic tools and preserve limitations.",
        source_path="tests/fixtures/skills/investigate/SKILL.md",
    )


def test_executes_allowlisted_read_only_tool() -> None:
    runner = GovernedToolRunner(registry=_registry(), skill=_skill())

    result = runner.run([ToolCallRequest(tool_name="echo", arguments={"value": "ok"})])

    assert result.status is RuntimeStatus.COMPLETED
    assert result.stop_reason == "all_tool_calls_completed"
    assert result.records[0].output == {"value": "ok"}


def test_unknown_tool_fails_closed() -> None:
    runner = GovernedToolRunner(registry=_registry(), skill=_skill())

    result = runner.run([ToolCallRequest(tool_name="shell", arguments={})])

    assert result.status is RuntimeStatus.BLOCKED
    assert result.stop_reason == "tool_not_registered"
    assert result.records[0].policy.reasons == ["tool_not_registered"]


def test_approval_required_tool_does_not_execute_without_approval() -> None:
    runner = GovernedToolRunner(
        registry=_registry(ToolRiskClass.APPROVAL_REQUIRED),
        skill=_skill(risk_level=SkillRiskLevel.CONTROLLED),
    )

    result = runner.run([ToolCallRequest(tool_name="echo", arguments={"value": "blocked"})])

    assert result.status is RuntimeStatus.APPROVAL_REQUIRED
    assert result.records[0].output is None


def test_approval_required_tool_executes_with_known_approval() -> None:
    approval_id = uuid4()
    runner = GovernedToolRunner(
        registry=_registry(ToolRiskClass.APPROVAL_REQUIRED),
        skill=_skill(risk_level=SkillRiskLevel.CONTROLLED),
        approved_ids={approval_id},
    )

    result = runner.run(
        [
            ToolCallRequest(
                tool_name="echo",
                arguments={"value": "approved"},
                approval_id=approval_id,
            )
        ]
    )

    assert result.status is RuntimeStatus.COMPLETED
    assert result.records[0].output == {"value": "approved"}


def test_repeated_tool_loop_is_blocked() -> None:
    runner = GovernedToolRunner(
        registry=_registry(),
        skill=_skill(),
        max_repeated_calls_per_tool=2,
    )

    request = ToolCallRequest(tool_name="echo", arguments={"value": "same"})
    result = runner.run([request, request, request])

    assert result.status is RuntimeStatus.BLOCKED
    assert result.stop_reason == "repeated_tool_call_limit_exceeded:echo"
    assert result.tool_call_count == 2


def test_invalid_input_is_returned_as_structured_failure() -> None:
    runner = GovernedToolRunner(registry=_registry(), skill=_skill())

    result = runner.run([ToolCallRequest(tool_name="echo", arguments={"unexpected": True})])

    assert result.status is RuntimeStatus.FAILED
    assert result.stop_reason == "tool_execution_failed"
    assert "ValidationError" in (result.records[0].error or "")

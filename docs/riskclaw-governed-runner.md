# RiskClaw governed tool runner

RiskClaw separates model planning from deterministic execution.

A planner may propose a `ToolCallRequest`, but `GovernedToolRunner` remains the enforcement boundary:

1. Resolve the tool from the deny-by-default registry.
2. Validate the proposal against the tool's Pydantic input model.
3. Apply the skill-scoped policy and optional canonical platform outcome.
4. Stop on blocked, unknown, over-budget, or repeated tool calls.
5. Require a known approval identifier before approval-gated handlers run.
6. Return a structured `AgentRunResult` for audit, replay, APIs, and evaluation.

## Responsibility split

```text
LLM or workflow proposes
        ↓
GovernedToolRunner validates
        ↓
ToolPolicyEngine constrains
        ↓
Typed deterministic handler executes
        ↓
AgentRunResult records outcome
```

The runner is model-agnostic. It can sit behind OpenAI Agents SDK, LangGraph, an MCP client, or a deterministic test planner without moving execution authority into the model.

## Example

```python
from pydantic import BaseModel

from riskclaw import (
    GovernedToolRunner,
    SkillDefinition,
    ToolCallRequest,
    ToolDefinition,
    ToolRegistry,
    ToolRiskClass,
)


class StatusInput(BaseModel):
    endpoint_id: str


registry = ToolRegistry()
registry.register(
    ToolDefinition(
        name="proxy_status",
        description="Read current proxy state.",
        risk_class=ToolRiskClass.READ_ONLY,
    ),
    input_model=StatusInput,
    handler=lambda payload: {"endpoint_id": payload.endpoint_id, "status": "direct"},
)

skill = SkillDefinition(
    name="endpoint_investigation",
    description="Read-only endpoint investigation.",
    allowed_tools=["proxy_status"],
    instructions="Collect evidence before producing a conclusion.",
    source_path="skills/endpoint-investigation/SKILL.md",
)

runner = GovernedToolRunner(registry=registry, skill=skill)
result = runner.run(
    [ToolCallRequest(tool_name="proxy_status", arguments={"endpoint_id": "demo-01"})]
)

print(result.model_dump_json(indent=2))
```

## Safety behavior

- Unknown tools are blocked.
- Tools outside the active skill are blocked.
- Tool inputs reject unknown fields when their input model does.
- The default run budget is 12 tool calls.
- The default repeated-call limit is 3 calls per tool.
- Approval-required tools do not execute without a known approval ID.
- Unknown canonical policy outcomes fail closed.
- Handler exceptions are converted into structured failures.

## Current limitation

This change adds the governed execution boundary, not an LLM planner. The next layer should translate a model's structured tool proposal into `ToolCallRequest` while keeping this runner unchanged and covered by deterministic regression tests.

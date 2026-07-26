"""RiskClaw tool-policy adapter tests."""

from __future__ import annotations

import pytest

from riskclaw.policy import ToolPolicyEngine
from riskclaw.schemas import (
    SkillDefinition,
    SkillRiskLevel,
    ToolDecision,
    ToolDefinition,
    ToolRiskClass,
)


def _tool(risk_class: ToolRiskClass, *, name: str = "proxy.collect") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Deterministic test tool.",
        risk_class=risk_class,
    )


def _skill(
    *,
    allowed_tools: list[str] | None = None,
    risk_level: SkillRiskLevel = SkillRiskLevel.READ_ONLY,
    requires_human_approval: bool = False,
) -> SkillDefinition:
    return SkillDefinition(
        name="proxy-risk-investigation",
        description="Investigate proxy reliability evidence.",
        allowed_tools=allowed_tools or ["proxy.collect"],
        risk_level=risk_level,
        requires_human_approval=requires_human_approval,
        instructions="Collect, classify, and preserve limitations.",
        source_path="riskclaw/skills/proxy-risk-investigation/SKILL.md",
    )


@pytest.mark.parametrize(
    ("risk_class", "skill_risk", "expected"),
    [
        (ToolRiskClass.READ_ONLY, SkillRiskLevel.READ_ONLY, ToolDecision.ALLOW),
        (ToolRiskClass.PREVIEW_ONLY, SkillRiskLevel.PREVIEW_ONLY, ToolDecision.PREVIEW),
        (
            ToolRiskClass.APPROVAL_REQUIRED,
            SkillRiskLevel.CONTROLLED,
            ToolDecision.REQUIRE_APPROVAL,
        ),
        (ToolRiskClass.BLOCKED, SkillRiskLevel.CONTROLLED, ToolDecision.BLOCK),
    ],
)
def test_intrinsic_tool_risk_maps_to_runtime_decision(
    risk_class: ToolRiskClass,
    skill_risk: SkillRiskLevel,
    expected: ToolDecision,
) -> None:
    result = ToolPolicyEngine().evaluate(
        tool=_tool(risk_class),
        skill=_skill(risk_level=skill_risk),
    )
    assert result.decision is expected


def test_skill_allowlist_blocks_unlisted_tool() -> None:
    result = ToolPolicyEngine().evaluate(
        tool=_tool(ToolRiskClass.READ_ONLY, name="tls.compare"),
        skill=_skill(),
    )
    assert result.decision is ToolDecision.BLOCK
    assert "tool_not_allowed_by_skill" in result.reasons


def test_read_only_skill_cannot_name_preview_tool() -> None:
    result = ToolPolicyEngine().evaluate(
        tool=_tool(ToolRiskClass.PREVIEW_ONLY),
        skill=_skill(risk_level=SkillRiskLevel.READ_ONLY),
    )
    assert result.decision is ToolDecision.BLOCK
    assert "tool_exceeds_skill_risk_boundary" in result.reasons


def test_canonical_policy_can_only_make_decision_more_restrictive() -> None:
    engine = ToolPolicyEngine()
    skill = _skill()
    tool = _tool(ToolRiskClass.READ_ONLY)

    preview = engine.evaluate(tool=tool, skill=skill, canonical_outcome="PREVIEW_ONLY")
    blocked = engine.evaluate(tool=tool, skill=skill, canonical_outcome="BLOCK")

    assert preview.decision is ToolDecision.PREVIEW
    assert blocked.decision is ToolDecision.BLOCK


def test_unknown_canonical_outcome_fails_closed() -> None:
    result = ToolPolicyEngine().evaluate(
        tool=_tool(ToolRiskClass.READ_ONLY),
        skill=_skill(),
        canonical_outcome="BYPASS",
    )
    assert result.decision is ToolDecision.BLOCK
    assert "unknown_canonical_outcome" in result.reasons


def test_rollback_required_fails_closed_in_phase_one() -> None:
    result = ToolPolicyEngine().evaluate(
        tool=_tool(ToolRiskClass.READ_ONLY),
        skill=_skill(),
        canonical_outcome="ROLLBACK_REQUIRED",
    )
    assert result.decision is ToolDecision.BLOCK
    assert "rollback_plan_requirement_not_satisfied" in result.reasons

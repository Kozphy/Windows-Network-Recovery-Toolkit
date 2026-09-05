"""Map tool and skill constraints onto the canonical platform policy vocabulary."""

from __future__ import annotations

from riskclaw.schemas import (
    SkillDefinition,
    SkillRiskLevel,
    ToolDecision,
    ToolDefinition,
    ToolPolicyResult,
    ToolRiskClass,
)

_TOOL_DEFAULTS: dict[ToolRiskClass, ToolDecision] = {
    ToolRiskClass.READ_ONLY: ToolDecision.ALLOW,
    ToolRiskClass.PREVIEW_ONLY: ToolDecision.PREVIEW,
    ToolRiskClass.APPROVAL_REQUIRED: ToolDecision.REQUIRE_APPROVAL,
    ToolRiskClass.BLOCKED: ToolDecision.BLOCK,
}

_CANONICAL_OUTCOMES: dict[str, ToolDecision] = {
    "ALLOW": ToolDecision.ALLOW,
    "PREVIEW_ONLY": ToolDecision.PREVIEW,
    "REQUIRE_HUMAN_APPROVAL": ToolDecision.REQUIRE_APPROVAL,
    "BLOCK": ToolDecision.BLOCK,
    # A rollback plan requirement cannot be represented safely by the four-state
    # runtime vocabulary, so Phase 1 fails closed.
    "ROLLBACK_REQUIRED": ToolDecision.BLOCK,
}

_RESTRICTIVENESS: dict[ToolDecision, int] = {
    ToolDecision.ALLOW: 0,
    ToolDecision.PREVIEW: 1,
    ToolDecision.REQUIRE_APPROVAL: 2,
    ToolDecision.BLOCK: 3,
}

_SKILL_MAX_RISK: dict[SkillRiskLevel, int] = {
    SkillRiskLevel.READ_ONLY: 0,
    SkillRiskLevel.PREVIEW_ONLY: 1,
    SkillRiskLevel.CONTROLLED: 2,
}

_TOOL_RISK: dict[ToolRiskClass, int] = {
    ToolRiskClass.READ_ONLY: 0,
    ToolRiskClass.PREVIEW_ONLY: 1,
    ToolRiskClass.APPROVAL_REQUIRED: 2,
    ToolRiskClass.BLOCKED: 3,
}


def _more_restrictive(left: ToolDecision, right: ToolDecision) -> ToolDecision:
    return left if _RESTRICTIVENESS[left] >= _RESTRICTIVENESS[right] else right


class ToolPolicyEngine:
    """Fail-closed policy evaluation for one skill-scoped tool proposal.

    The engine is an adapter, not a replacement for
    ``src.platform_core.policy.evaluate_policy``. Callers may pass that engine's
    outcome through ``canonical_outcome``; RiskClaw can only make the result more
    restrictive.
    """

    def evaluate(
        self,
        *,
        tool: ToolDefinition,
        skill: SkillDefinition,
        canonical_outcome: str | None = None,
    ) -> ToolPolicyResult:
        reasons: list[str] = []

        if tool.name not in skill.allowed_tools:
            return ToolPolicyResult(
                tool_name=tool.name,
                skill_name=skill.name,
                decision=ToolDecision.BLOCK,
                reasons=["tool_not_allowed_by_skill"],
                canonical_outcome=canonical_outcome,
            )

        if _TOOL_RISK[tool.risk_class] > _SKILL_MAX_RISK[skill.risk_level]:
            return ToolPolicyResult(
                tool_name=tool.name,
                skill_name=skill.name,
                decision=ToolDecision.BLOCK,
                reasons=["tool_exceeds_skill_risk_boundary"],
                canonical_outcome=canonical_outcome,
            )

        decision = _TOOL_DEFAULTS[tool.risk_class]
        reasons.append(f"tool_risk_class:{tool.risk_class.value}")

        if skill.requires_human_approval and decision is not ToolDecision.BLOCK:
            decision = _more_restrictive(decision, ToolDecision.REQUIRE_APPROVAL)
            reasons.append("skill_requires_human_approval")

        if canonical_outcome is not None:
            normalized = canonical_outcome.strip().upper()
            canonical_decision = _CANONICAL_OUTCOMES.get(normalized)
            if canonical_decision is None:
                decision = ToolDecision.BLOCK
                reasons.append("unknown_canonical_outcome")
            else:
                decision = _more_restrictive(decision, canonical_decision)
                reasons.append(f"canonical_outcome:{normalized}")
                if normalized == "ROLLBACK_REQUIRED":
                    reasons.append("rollback_plan_requirement_not_satisfied")

        return ToolPolicyResult(
            tool_name=tool.name,
            skill_name=skill.name,
            decision=decision,
            reasons=reasons,
            canonical_outcome=canonical_outcome,
        )

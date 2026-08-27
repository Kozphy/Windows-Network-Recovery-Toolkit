"""Recommendation vs execution separation + fixture remediation."""

from __future__ import annotations

from typing import Any

from src.purple_team.models import (
    DetectionResult,
    Recommendation,
    RemediationOutcome,
    ScenarioDefinition,
)


def recommend(
    scenario: ScenarioDefinition,
    detections: list[DetectionResult],
) -> Recommendation:
    detected = any(d.detected for d in detections)
    action = scenario.expected_response if detected else "observe"
    high_impact = scenario.risk_level.lower() in {"high", "critical", "medium"}
    return Recommendation(
        action=action,
        dry_run_default=True,
        confirmation_token="PURPLE_TEAM_LAB_ONLY" if high_impact and detected else None,
        rationale=(
            f"Detection fired; recommend '{action}' under policy gate."
            if detected
            else "No detection — observe only."
        ),
        requires_human_approval=bool(high_impact and detected),
    )


def approve(
    recommendation: Recommendation,
    *,
    dry_run: bool,
    approved: bool,
) -> tuple[bool, str]:
    """Return (may_execute, reason). Recommendation ≠ execution."""
    if dry_run:
        return False, "dry_run_blocks_execution"
    if not recommendation.requires_human_approval:
        return True, "low_risk_auto_allowed_lab"
    if approved:
        return True, "human_approved"
    return False, "awaiting_human_approval"


def remediate_fixture(
    scenario: ScenarioDefinition,
    fixture: dict[str, Any],
    recommendation: Recommendation,
    *,
    dry_run: bool,
    approved: bool,
) -> RemediationOutcome:
    """Fixture-scoped remediation: flip post_state toward baseline without host mutation."""
    may_exec, reason = approve(recommendation, dry_run=dry_run, approved=approved)
    limitations = [
        "Remediation here mutates in-memory fixture state only — not live WinINET.",
        "Command success is never treated as recovery without verification.",
        f"approval_gate:{reason}",
    ]
    if dry_run or not may_exec:
        return RemediationOutcome(
            recommended=True,
            executed=False,
            success=False,
            dry_run=dry_run,
            details={"reason": reason, "planned_action": recommendation.action},
            limitations=limitations,
        )

    baseline = dict(fixture.get("baseline_state") or fixture.get("pre_state") or {})
    # Simulate successful apply into fixture working state.
    fixture["remediated_state"] = baseline
    fixture["remediation_command_success"] = True
    return RemediationOutcome(
        recommended=True,
        executed=True,
        success=True,
        dry_run=False,
        details={
            "reason": reason,
            "action": recommendation.action,
            "remediated_state": baseline,
            "command_success": True,
        },
        limitations=limitations,
    )

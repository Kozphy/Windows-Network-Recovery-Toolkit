"""Explicit safety gate — deny by default for purple scenario execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.purple_team.models import ScenarioDefinition


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reasons: list[str]
    checks: dict[str, bool]
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Explicit authorization flag for non-dry-run fixture runs (never production).
PURPLE_AUTH_ENV = "PURPLE_TEAM_AUTHORIZED"
PURPLE_AUTH_TOKEN = "PURPLE_TEAM_LAB_ONLY"


def evaluate_safety(
    scenario: ScenarioDefinition,
    *,
    dry_run: bool,
    authorized: bool,
    environment: str = "lab",
    target_is_remote: bool = False,
    target_is_production: bool = False,
) -> SafetyDecision:
    """ALLOW only when all hard gates pass; otherwise DENY with reasons."""
    checks = {
        "safe_for_local_execution": scenario.safe_for_local_execution,
        "cleanup_required": scenario.cleanup.required and bool(scenario.cleanup.steps),
        "preconditions_declared": bool(scenario.preconditions),
        "no_remote_target": not target_is_remote and not scenario.allows_remote_target,
        "no_production_target": (
            not target_is_production and not scenario.allows_production_target
        ),
        "supported_environment": environment in {"lab", "ci", "fixture"},
        "authorized_or_dry_run": dry_run
        or authorized
        or not scenario.authorized_execution_required,
        "fixture_simulation": bool(scenario.simulation.fixture_path),
    }
    reasons: list[str] = []
    for name, ok in checks.items():
        if not ok:
            reasons.append(f"failed:{name}")

    limitations = [
        "Purple simulations are fixture-driven control tests — not real adversary emulation.",
        "Dry-run never mutates host state.",
        "Authorization does not imply safety for live Windows mutation outside fixtures.",
        "Policy ALLOW ≠ safety guarantee.",
        *list(scenario.limitations),
    ]

    structural_ok = all(
        checks[k]
        for k in (
            "safe_for_local_execution",
            "cleanup_required",
            "preconditions_declared",
            "no_remote_target",
            "no_production_target",
            "supported_environment",
            "fixture_simulation",
        )
    )
    if dry_run and structural_ok:
        return SafetyDecision(
            allowed=True,
            reasons=["dry_run_preview"],
            checks=checks,
            limitations=limitations,
        )

    allowed = all(checks.values())
    if not allowed and not reasons:
        reasons.append("denied_by_default")
    return SafetyDecision(
        allowed=allowed,
        reasons=reasons if not allowed else ["authorized_lab_fixture_run"],
        checks=checks,
        limitations=limitations,
    )

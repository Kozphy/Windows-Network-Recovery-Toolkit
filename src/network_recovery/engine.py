"""Scenario diagnosis orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .collectors import collect_signals
from .diagnosis_text import format_diagnosis_report
from .models import (
    SCENARIO_CHATGPT_APP_FIREWALL,
    DiagnosisResult,
    PolicyOutcome,
    SignalBundle,
    VerificationStatus,
    new_run_id,
)
from .remediation_catalog import remediation_previews_for_chatgpt_scenario
from .scenarios.chatgpt_app_firewall import analyze_chatgpt_app_firewall


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run_scenario_diagnosis(
    scenario: str,
    *,
    signals: SignalBundle | None = None,
    recovery_firewall_reset_helped: bool | None = None,
    dry_run: bool = True,
    collect_live: bool = True,
    run: Any = None,
) -> DiagnosisResult:
    """Run one app-path scenario and build a replayable diagnosis result."""
    if scenario != SCENARIO_CHATGPT_APP_FIREWALL:
        raise ValueError(f"Unknown scenario: {scenario}")

    if signals is None:
        if not collect_live:
            raise ValueError("signals required when collect_live=False")
        kwargs: dict[str, Any] = {}
        if run is not None:
            kwargs["run"] = run
        signals = collect_signals(**kwargs)

    analysis = analyze_chatgpt_app_firewall(
        signals,
        recovery_firewall_reset_helped=recovery_firewall_reset_helped,
    )
    hypotheses = analysis["hypotheses"]  # type: ignore[index]
    verification_status: VerificationStatus = analysis["verification_status"]  # type: ignore[assignment]

    actions = remediation_previews_for_chatgpt_scenario(dry_run=dry_run)
    policy: PolicyOutcome = "PREVIEW"
    if dry_run:
        policy = "PREVIEW"
    elif any(a.policy_decision == "ALLOW" for a in actions):
        policy = "ALLOW"

    primary_id = hypotheses[0].hypothesis_id if hypotheses else "unknown"
    human = format_diagnosis_report(
        signals=signals,
        events=list(analysis["events"]),  # type: ignore[arg-type]
        hypotheses=hypotheses,
        verification_status=verification_status,
        primary_hypothesis_id=primary_id,
        recovery_firewall_reset_helped=recovery_firewall_reset_helped,
    )

    return DiagnosisResult(
        run_id=new_run_id(),
        scenario_id=SCENARIO_CHATGPT_APP_FIREWALL,
        canonical_case=str(analysis["canonical_case"]),
        timestamp=_utc_now_iso(),
        signals=signals,
        events=list(analysis["events"]),  # type: ignore[arg-type]
        hypotheses=hypotheses,
        confidence_boundary=str(analysis["confidence_boundary"]),
        recommended_actions=actions,
        policy_decision=policy,
        verification_status=verification_status,
        human_summary=human,
        limitations=list(analysis["limitations"]),  # type: ignore[arg-type]
        post_check_results={},
        remediation_executed=[],
    )

"""Outcome classification — deterministic, not autonomous AI."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class OutcomeClassification(StrEnum):
    SUCCESSFUL_REMEDIATION = "SUCCESSFUL_REMEDIATION"
    PARTIAL_RECOVERY = "PARTIAL_RECOVERY"
    NO_IMPACT = "NO_IMPACT"
    REGRESSION = "REGRESSION"
    INCONCLUSIVE = "INCONCLUSIVE"


def classify_outcome(
    *,
    was_successful: bool | None,
    was_false_positive: bool | None = None,
    was_blocked_by_policy: bool = False,
    rollback_required: bool = False,
    notes: str = "",
) -> OutcomeClassification:
    if was_blocked_by_policy:
        return OutcomeClassification.NO_IMPACT
    if rollback_required or was_false_positive:
        return OutcomeClassification.REGRESSION
    if was_successful is True:
        return OutcomeClassification.SUCCESSFUL_REMEDIATION
    if was_successful is False:
        return OutcomeClassification.PARTIAL_RECOVERY
    if "partial" in notes.lower():
        return OutcomeClassification.PARTIAL_RECOVERY
    return OutcomeClassification.INCONCLUSIVE


def outcome_record_fields(
    *,
    decision_id: str,
    evidence_tier: str,
    policy_gate: str,
    remediation_preview: dict[str, Any] | None,
    actual_result: str,
    classification: OutcomeClassification,
    rollback_required: bool,
) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "evidence_tier": evidence_tier,
        "policy_gate": policy_gate,
        "remediation_preview": remediation_preview or {},
        "actual_result": actual_result,
        "classification": classification.value,
        "rollback_required": rollback_required,
    }

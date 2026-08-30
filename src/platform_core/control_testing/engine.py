"""Deterministic evaluator for evidence-backed control tests."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import (
    ControlDefinition,
    ControlTestResult,
    TestConclusion,
    make_test_id,
)


def _tier_number(value: Any) -> int:
    """Normalize T0..T5 labels or integers without upgrading missing evidence."""

    if isinstance(value, int):
        return max(0, min(value, 5))
    text = str(value or "").upper()
    if text.startswith("T") and len(text) > 1 and text[1].isdigit():
        return max(0, min(int(text[1]), 5))
    return 0


def evaluate_control(
    control: ControlDefinition,
    evidence: Iterable[dict[str, Any]],
    *,
    incident_id: str,
    tested_at_utc: str,
) -> ControlTestResult:
    """Evaluate a control against supplied normalized evidence.

    Evidence rows are expected to contain ``event_id``, ``evidence_type``,
    ``evidence_tier`` and ``normalized_fields``. Unknown or malformed rows are
    ignored rather than interpreted optimistically.
    """

    rows = [row for row in evidence if isinstance(row, dict)]
    evidence_refs = tuple(
        sorted({str(row.get("event_id")) for row in rows if row.get("event_id")})
    )
    satisfied: list[str] = []
    missing: list[str] = []

    for requirement in control.requirements:
        matched = False
        for row in rows:
            if str(row.get("evidence_type") or "") != requirement.evidence_type:
                continue
            if _tier_number(row.get("evidence_tier")) < requirement.minimum_tier:
                continue
            fields = row.get("normalized_fields")
            if not isinstance(fields, dict):
                continue
            if all(field in fields and fields[field] is not None for field in requirement.required_fields):
                matched = True
                break
        label = requirement.description or requirement.evidence_type
        if matched:
            satisfied.append(label)
        else:
            missing.append(label)

    if not rows:
        conclusion = TestConclusion.NOT_TESTED
        rationale = "No evidence rows were supplied; the control was not tested."
    elif not missing:
        conclusion = TestConclusion.PASS
        rationale = "All explicit evidence requirements were satisfied."
    elif satisfied:
        conclusion = TestConclusion.PARTIAL
        rationale = "Some evidence requirements were satisfied; missing evidence remains."
    else:
        conclusion = TestConclusion.FAIL
        rationale = "Evidence was supplied, but none of the explicit requirements were satisfied."

    return ControlTestResult(
        test_id=make_test_id(
            control_id=control.control_id,
            control_version=control.version,
            incident_id=incident_id,
            evidence_refs=evidence_refs,
        ),
        control_id=control.control_id,
        control_version=control.version,
        incident_id=incident_id,
        conclusion=conclusion,
        tested_at_utc=tested_at_utc,
        evidence_refs=evidence_refs,
        satisfied_requirements=tuple(satisfied),
        missing_requirements=tuple(missing),
        rationale=rationale,
        limitations=control.limitations,
    )


def evaluate_controls(
    controls: Iterable[ControlDefinition],
    evidence: Iterable[dict[str, Any]],
    *,
    incident_id: str,
    tested_at_utc: str,
) -> list[ControlTestResult]:
    """Evaluate multiple controls over the same immutable evidence snapshot."""

    snapshot = list(evidence)
    return [
        evaluate_control(
            control,
            snapshot,
            incident_id=incident_id,
            tested_at_utc=tested_at_utc,
        )
        for control in controls
    ]

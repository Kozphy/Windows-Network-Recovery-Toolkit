"""Enterprise risk scoring — inherent and residual."""

from __future__ import annotations

import uuid
from typing import Any

from src.platform_core.enterprise.enums import RiskLevel, Severity, TestResult
from src.platform_core.findings.models import Finding
from src.platform_core.risk_assessment.models import RiskAssessment, RiskRegisterEntry
from src.platform_core.threats.models import Threat

_LEVEL_RANK = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def _combine(likelihood: RiskLevel, impact: RiskLevel) -> RiskLevel:
    score = (_LEVEL_RANK[likelihood] + _LEVEL_RANK[impact]) / 2
    if score >= 3.5:
        return RiskLevel.CRITICAL
    if score >= 2.5:
        return RiskLevel.HIGH
    if score >= 1.5:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _apply_controls(inherent: RiskLevel, effectiveness: float) -> RiskLevel:
    reduced = max(1, _LEVEL_RANK[inherent] - int(effectiveness * 2))
    for level, rank in _LEVEL_RANK.items():
        if rank == reduced:
            return level
    return RiskLevel.LOW


def assess_risks(
    findings: list[Finding],
    threats: list[Threat],
    tests: list[Any],
) -> tuple[list[RiskAssessment], list[RiskRegisterEntry]]:
    pass_count = sum(1 for t in tests if t.result == TestResult.PASS)
    total = max(len(tests), 1)
    effectiveness = pass_count / total

    assessments: list[RiskAssessment] = []
    register: list[RiskRegisterEntry] = []

    threat = threats[0] if threats else None
    for finding in findings:
        likelihood = threat.likelihood if threat else RiskLevel.MEDIUM
        impact = threat.impact if threat else RiskLevel.MEDIUM
        inherent = _combine(likelihood, impact)
        if finding.severity == Severity.CRITICAL:
            inherent = RiskLevel.CRITICAL
        elif finding.severity == Severity.HIGH and _LEVEL_RANK[inherent] < 3:
            inherent = RiskLevel.HIGH

        residual = _apply_controls(inherent, effectiveness)
        rid = f"RSK-{uuid.uuid4().hex[:8]}"
        assessments.append(
            RiskAssessment(
                risk_id=rid,
                finding_id=finding.finding_id,
                threat_id=threat.threat_id if threat else "THR-000",
                inherent_risk=inherent,
                residual_risk=residual,
                likelihood=likelihood,
                impact=impact,
                control_effectiveness=round(effectiveness, 4),
                limitations=[
                    "Risk scores are ordinal governance inputs, not actuarial probability.",
                    "Observation is not proof.",
                ],
            )
        )
        register.append(
            RiskRegisterEntry(
                risk_id=rid,
                title=finding.description[:120],
                inherent_risk=inherent,
                residual_risk=residual,
                owner="Technology Risk",
                linked_findings=[finding.finding_id],
            )
        )
    return assessments, register

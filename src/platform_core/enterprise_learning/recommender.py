"""Continuous improvement recommendations from outcomes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import TestResult
from src.platform_core.control_testing.models import ControlTestExecution


class LearningRecommendation(BaseModel):
    category: str
    recommendation: str
    rationale: str
    limitations: list[str] = Field(default_factory=list)


def generate_learning_recommendations(
    tests: list[ControlTestExecution],
    fixture: dict[str, Any],
) -> list[LearningRecommendation]:
    recs: list[LearningRecommendation] = []
    failed = [t for t in tests if t.result == TestResult.FAIL]
    warnings = [t for t in tests if t.result == TestResult.WARNING]

    if any(t.control_id == "NET-001" for t in failed):
        recs.append(
            LearningRecommendation(
                category="control",
                recommendation="Increase frequency of proxy baseline validation on high-criticality endpoints.",
                rationale="Recurring proxy baseline failures detected in fixture analysis.",
                limitations=["Based on synthetic/fixture evidence until fleet telemetry wired."],
            )
        )
    if any(t.control_id == "NET-002" for t in warnings):
        recs.append(
            LearningRecommendation(
                category="test",
                recommendation="Enable Sysmon E13 collection for registry writer proof on proxy incidents.",
                rationale="Registry integrity tests returned WARNING without writer telemetry.",
            )
        )
    classification = (fixture.get("classification") or {}).get("primary_classification", "")
    if classification == "REMEDIATION_NOT_STICKY" or fixture.get("timeline"):
        recs.append(
            LearningRecommendation(
                category="policy",
                recommendation="Add reverter detection policy before repeat remediation preview.",
                rationale="Stickiness failure pattern suggests active reverter.",
                limitations=["Correlation is not causation."],
            )
        )
    if not recs:
        recs.append(
            LearningRecommendation(
                category="governance",
                recommendation="Maintain current control test cadence; review quarterly.",
                rationale="No failed controls in current assessment window.",
            )
        )
    return recs

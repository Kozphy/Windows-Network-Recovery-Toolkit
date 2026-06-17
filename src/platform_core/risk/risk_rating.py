"""Risk rating models with mandatory limitations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .control_test import ControlTest, ControlTestResult
from .finding import Finding


class RiskRating(BaseModel):
    rating_id: str
    inherent_level: str
    residual_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    likelihood: str = "medium"
    impact: str = "medium"
    control_effectiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    limitations: list[str] = Field(default_factory=list)
    summary: str = ""


_HIGH_CLASSIFICATIONS = {"POSSIBLE_MITM_RISK", "SUSPICIOUS_PROXY", "REVERTER_SUSPECTED"}
_MEDIUM_CLASSIFICATIONS = {"DEAD_PROXY_CONFIG", "UNKNOWN_LOCAL_PROXY", "WININET_WINHTTP_MISMATCH"}


def rate_risk(findings: list[Finding], tests: list[ControlTest], fixture: dict[str, Any]) -> RiskRating:
    classification = (fixture.get("classification") or {}).get("primary_classification", "")
    confidence = float((fixture.get("classification") or {}).get("confidence") or 0.5)
    proof = (fixture.get("proof") or {}).get("conclusion") or {}
    proof_status = proof.get("status", "not_run")

    if classification in _HIGH_CLASSIFICATIONS and proof_status == "supported":
        inherent = "high"
        impact = "high"
    elif classification in _HIGH_CLASSIFICATIONS:
        inherent = "medium"
        impact = "high"
    elif classification in _MEDIUM_CLASSIFICATIONS:
        inherent = "medium"
        impact = "medium"
    else:
        inherent = "low"
        impact = "medium"

    passed = sum(1 for t in tests if t.result == ControlTestResult.PASS)
    total = max(len(tests), 1)
    effectiveness = round(passed / total, 2)
    residual = inherent
    if effectiveness >= 0.6 and inherent == "high":
        residual = "medium"
    elif effectiveness >= 0.75 and inherent == "medium":
        residual = "low"

    limitations = [
        "Confidence is ordinal (0–1), not a statistical probability.",
        "Correlation and proof do not equal final causation without strong telemetry.",
        "This rating supports governance discussion; it is not a regulatory attestation.",
    ]
    if any(f.requires_validation for f in findings):
        limitations.append("One or more findings require additional validation before escalation.")

    return RiskRating(
        rating_id="RR_INCIDENT_001",
        inherent_level=inherent,
        residual_level=residual,
        confidence=confidence,
        likelihood="medium" if classification in _MEDIUM_CLASSIFICATIONS else inherent,
        impact=impact,
        control_effectiveness=effectiveness,
        limitations=limitations,
        summary=(
            f"Inherent {inherent} / residual {residual} for {classification} "
            f"(proof: {proof_status})."
        ),
    )

"""Finding models — evidence-gated only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .control_test import ControlTest, ControlTestResult


class Finding(BaseModel):
    finding_id: str
    title: str
    classification: str
    evidence_tier: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    requires_validation: bool = False


def _has_real_evidence(test: ControlTest) -> bool:
    if not test.evidence:
        return False
    if test.evidence.keys() == {"note"}:
        return False
    return True


def findings_from_fixture(fixture: dict[str, Any], tests: list[ControlTest]) -> list[Finding]:
    classification = fixture.get("classification") or {}
    proof = fixture.get("proof") or {}
    primary = classification.get("primary_classification", "UNCLASSIFIED")
    secondary = classification.get("secondary_signals") or []
    confidence = float(classification.get("confidence") or 0.0)
    proof_status = (proof.get("conclusion") or {}).get("status", "not_run")

    evidence_tier = "observation"
    if proof_status == "supported":
        evidence_tier = "proof"
    elif any(t.result == ControlTestResult.PASS and t.test_id == "CT_WRITER_ATTRIBUTION" for t in tests):
        evidence_tier = "correlation"

    findings: list[Finding] = [
        Finding(
            finding_id=f"FND_{primary}",
            title=primary.replace("_", " ").title(),
            classification=primary,
            evidence_tier=evidence_tier,
            confidence=confidence,
            summary=classification.get("reasoning", "See classification evidence."),
            evidence={
                "secondary_signals": secondary,
                "classification_evidence": classification.get("evidence", []),
            },
            limitations=list(classification.get("limitations") or []),
            requires_validation=primary in {"UNKNOWN_LOCAL_PROXY", "POSSIBLE_MITM_RISK", "SUSPICIOUS_PROXY"},
        )
    ]

    if "WININET_WINHTTP_MISMATCH" in secondary:
        findings.append(
            Finding(
                finding_id="FND_WININET_WINHTTP_MISMATCH",
                title="WinINET and WinHTTP proxy paths diverge",
                classification="WININET_WINHTTP_MISMATCH",
                evidence_tier=evidence_tier,
                confidence=confidence,
                summary="Browser stack proxy differs from WinHTTP direct configuration.",
                evidence={"secondary_signals": secondary},
                limitations=["Mismatch indicates configuration drift, not proven malicious intent."],
            )
        )

    for test in tests:
        if test.result == ControlTestResult.FAIL and _has_real_evidence(test):
            findings.append(
                Finding(
                    finding_id=f"FND_{test.test_id}",
                    title=f"Control test failed: {test.control_name}",
                    classification=test.test_id,
                    evidence_tier="observation",
                    confidence=0.5,
                    summary=test.finding_summary,
                    evidence=test.evidence,
                    limitations=test.limitations,
                )
            )

    return findings

"""Executive governance metrics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.control_testing.models import ControlTestExecution
from src.platform_core.enterprise.enums import Severity, TestResult
from src.platform_core.findings.models import Finding
from src.platform_core.remediation_lifecycle.models import RemediationItem
from src.platform_core.enterprise.enums import RemediationState


class GovernanceDashboard(BaseModel):
    controls_tested: int = 0
    controls_passed: int = 0
    controls_failed: int = 0
    controls_warning: int = 0
    high_risk_findings: int = 0
    critical_findings: int = 0
    open_remediations: int = 0
    compliance_percentage: float = Field(ge=0.0, le=100.0)
    audiences: dict[str, str] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def build_governance_dashboard(
    tests: list[ControlTestExecution],
    findings: list[Finding],
    remediations: list[RemediationItem],
) -> GovernanceDashboard:
    passed = sum(1 for t in tests if t.result == TestResult.PASS)
    failed = sum(1 for t in tests if t.result == TestResult.FAIL)
    warning = sum(1 for t in tests if t.result == TestResult.WARNING)
    total = len(tests) or 1
    compliance = round((passed / total) * 100, 2)

    return GovernanceDashboard(
        controls_tested=len(tests),
        controls_passed=passed,
        controls_failed=failed,
        controls_warning=warning,
        high_risk_findings=sum(1 for f in findings if f.severity in (Severity.HIGH, Severity.CRITICAL)),
        critical_findings=sum(1 for f in findings if f.severity == Severity.CRITICAL),
        open_remediations=sum(
            1 for r in remediations if r.status in (RemediationState.OPEN, RemediationState.PLANNED)
        ),
        compliance_percentage=compliance,
        audiences={
            "CIO": "Service availability and control compliance %",
            "CISO": "High-risk findings and TLS/proxy threat exposure",
            "Internal Audit": "Control test evidence and audit trail completeness",
            "Risk Committee": "Inherent vs residual risk register entries",
            "Board": "Aggregate compliance % and critical finding count (summary only)",
        },
        limitations=[
            "Metrics derived from fixture or collected evidence — not certified compliance.",
            "Compliance % reflects control test pass rate, not regulatory attestation.",
        ],
    )

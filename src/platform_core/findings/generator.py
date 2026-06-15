"""Generate findings from failed or warning control tests."""

from __future__ import annotations

import uuid
from typing import Any

from src.platform_core.control_testing.models import ControlTestExecution
from src.platform_core.enterprise.enums import Severity, TestResult
from src.platform_core.findings.models import Finding


def _severity_for_test(test: ControlTestExecution, fixture: dict[str, Any]) -> Severity:
    if test.result == TestResult.FAIL:
        cls_sev = (fixture.get("classification") or {}).get("severity", "medium")
        if cls_sev == "critical" or test.control_id == "NET-003":
            return Severity.HIGH
        return Severity.MEDIUM
    if test.result == TestResult.WARNING:
        return Severity.MEDIUM
    return Severity.LOW


def generate_findings(
    tests: list[ControlTestExecution],
    fixture: dict[str, Any],
    *,
    asset_ids: list[str],
) -> list[Finding]:
    findings: list[Finding] = []
    for test in tests:
        if test.result not in (TestResult.FAIL, TestResult.WARNING):
            continue
        sev = _severity_for_test(test, fixture)
        rec = "Generate remediation preview; do not auto-execute without policy gates."
        if test.control_id == "NET-003":
            rec = "Defer containment; collect writer telemetry and security review."
        elif test.control_id == "NET-001":
            rec = "Preview WinINET proxy disable with typed confirmation after proof review."
        findings.append(
            Finding(
                finding_id=f"FND-{uuid.uuid4().hex[:8]}",
                severity=sev,
                description=(
                    f"Control {test.control_id} ({test.control_name}) "
                    f"resulted in {test.result.value}."
                ),
                impacted_assets=asset_ids,
                control_id=test.control_id,
                test_id=test.test_id,
                evidence=test.evidence,
                recommendation=rec,
                limitations=test.limitations,
            )
        )
    return findings

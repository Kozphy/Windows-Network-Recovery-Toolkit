"""Control test execution models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .control import ControlObjective, controls_for_fixture


class ControlTestResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_TESTED = "NOT_TESTED"


class ControlTest(BaseModel):
    test_id: str
    control_id: str
    control_name: str
    procedure: str
    execution_time: str
    result: ControlTestResult
    evidence: dict[str, Any] = Field(default_factory=dict)
    finding_summary: str = ""
    limitations: list[str] = Field(default_factory=list)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_control_tests(fixture: dict[str, Any]) -> list[ControlTest]:
    controls = {c.control_id: c for c in controls_for_fixture(fixture)}
    classification = fixture.get("classification") or {}
    proof = fixture.get("proof") or {}
    policy = fixture.get("policy_decision") or {}
    primary = classification.get("primary_classification", "")
    secondary = classification.get("secondary_signals") or []
    conclusion = (proof.get("conclusion") or {}).get("status", "not_run")
    dry_run = bool(fixture.get("dry_run", True) or policy.get("dry_run", True))
    outcome = policy.get("outcome", "PREVIEW_ONLY")

    tests: list[ControlTest] = []

    drift_result = ControlTestResult.FAIL if "WININET_WINHTTP_MISMATCH" in secondary else ControlTestResult.PASS
    tests.append(
        ControlTest(
            test_id="CT_PROXY_DRIFT",
            control_id="CTRL_PROXY_MONITOR",
            control_name=controls["CTRL_PROXY_MONITOR"].name,
            procedure="Compare WinINET, WinHTTP, listener state, and path contrast.",
            execution_time=_now_utc(),
            result=drift_result,
            evidence={
                "classification": primary,
                "secondary_signals": secondary,
                "listener_found": (fixture.get("proxy_owner") or {}).get("listener_found"),
            },
            finding_summary=f"{primary} with signals {', '.join(secondary) or 'none'}",
            limitations=["Observation of configuration state; proof tier may differ."],
        )
    )

    if conclusion == "supported":
        proof_result = ControlTestResult.PASS
    elif conclusion in ("weakened", "inconclusive"):
        proof_result = ControlTestResult.WARNING
    elif conclusion == "not_run":
        proof_result = ControlTestResult.NOT_TESTED
    else:
        proof_result = ControlTestResult.FAIL
    tests.append(
        ControlTest(
            test_id="CT_PROOF_ENVELOPE",
            control_id="CTRL_PROXY_MONITOR",
            control_name="Structured proof envelope",
            procedure="Run diagnose --proof contrast checks.",
            execution_time=_now_utc(),
            result=proof_result,
            evidence={"proof_conclusion": conclusion, "confidence": (proof.get("conclusion") or {}).get("confidence")},
            finding_summary=f"Proof conclusion: {conclusion}",
            limitations=proof.get("limitations") or [],
        )
    )

    writer = fixture.get("writer_attribution") or {}
    if writer:
        writer_result = (
            ControlTestResult.PASS
            if writer.get("attribution_tier") in ("PROVEN_REGISTRY_WRITER", "CORRELATED")
            else ControlTestResult.WARNING
        )
    else:
        writer_result = ControlTestResult.NOT_TESTED
    tests.append(
        ControlTest(
            test_id="CT_WRITER_ATTRIBUTION",
            control_id="CTRL_WRITER_ATTRIBUTION",
            control_name=controls["CTRL_WRITER_ATTRIBUTION"].name,
            procedure="Correlate registry changes with process writer telemetry.",
            execution_time=_now_utc(),
            result=writer_result,
            evidence=writer or {"note": "No writer telemetry in fixture scope."},
            finding_summary=writer.get("finding", "Writer attribution not in scope"),
            limitations=["Correlation is not final causation without network impact proof."],
        )
    )

    remediation_pass = dry_run and outcome in ("PREVIEW_ONLY", "REQUIRE_TYPED_CONFIRMATION")
    tests.append(
        ControlTest(
            test_id="CT_REMEDIATION_SAFETY",
            control_id="CTRL_REMEDIATION_GOVERNANCE",
            control_name=controls["CTRL_REMEDIATION_GOVERNANCE"].name,
            procedure="Verify dry-run default, typed confirmation, no silent destructive actions.",
            execution_time=_now_utc(),
            result=ControlTestResult.PASS if remediation_pass else ControlTestResult.WARNING,
            evidence={"dry_run": dry_run, "policy_outcome": outcome, "policy": policy},
            finding_summary=outcome,
            limitations=["Policy permission does not guarantee operational safety."],
        )
    )

    audit_available = fixture.get("audit_chain_valid")
    if audit_available is True:
        audit_result = ControlTestResult.PASS
    elif audit_available is False:
        audit_result = ControlTestResult.FAIL
    else:
        audit_result = ControlTestResult.NOT_TESTED
    tests.append(
        ControlTest(
            test_id="CT_AUDIT_CHAIN",
            control_id="CTRL_AUDIT_TRAIL",
            control_name=controls["CTRL_AUDIT_TRAIL"].name,
            procedure="Verify append-only hash-chained audit and replay determinism.",
            execution_time=_now_utc(),
            result=audit_result,
            evidence={"audit_chain_valid": audit_available},
            finding_summary="Audit chain valid" if audit_available else "Audit verification not run",
            limitations=["Local disk access can still tamper with logs outside hardened deployment."],
        )
    )

    return tests

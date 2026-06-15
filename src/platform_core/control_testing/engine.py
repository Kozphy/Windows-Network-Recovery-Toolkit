"""Control testing engine — fixture-safe, evidence-backed."""

from __future__ import annotations

import uuid
from typing import Any

from platform_core.models import utc_now_iso

from src.platform_core.control_testing.models import ControlTestExecution
from src.platform_core.controls.catalog import controls_for_classification
from src.platform_core.enterprise.enums import TestResult


def _test_proxy_baseline(fixture: dict[str, Any]) -> ControlTestExecution:
    state = fixture.get("proxy_state") or {}
    classification = (fixture.get("classification") or {}).get("primary_classification", "")
    enabled = state.get("wininet_proxy_enabled")
    listener = (fixture.get("proxy_owner") or {}).get("listener_found")
    port = state.get("localhost_port")

    if classification == "DEAD_PROXY_CONFIG":
        result = TestResult.FAIL
        evidence = {
            "proxy_enabled": enabled,
            "listener_found": listener,
            "localhost_port": port,
            "classification": classification,
        }
    elif classification == "NO_PROXY":
        result = TestResult.PASS
        evidence = {"proxy_enabled": enabled, "classification": classification}
    elif classification == "UNKNOWN_LOCAL_PROXY":
        result = TestResult.WARNING
        evidence = {"listener_found": listener, "classification": classification}
    else:
        result = TestResult.WARNING
        evidence = {"classification": classification or "unknown"}

    return ControlTestExecution(
        test_id=f"TST-{uuid.uuid4().hex[:8]}",
        control_id="NET-001",
        control_name="Proxy Baseline Validation",
        execution_time=utc_now_iso(),
        result=result,
        evidence=evidence,
        limitations=[
            "Observation is not proof.",
            "Listener correlation is not registry-writer proof.",
        ],
    )


def _test_registry_integrity(fixture: dict[str, Any]) -> ControlTestExecution:
    writer = fixture.get("writer_attribution") or {}
    confirmed = writer.get("registry_writer_confirmed", False)
    classification = (fixture.get("classification") or {}).get("primary_classification", "")

    if classification == "UNKNOWN_LOCAL_PROXY" and not confirmed:
        result = TestResult.WARNING
    elif confirmed:
        result = TestResult.PASS
    else:
        result = TestResult.NOT_TESTED

    return ControlTestExecution(
        test_id=f"TST-{uuid.uuid4().hex[:8]}",
        control_id="NET-002",
        control_name="Registry Integrity Validation",
        execution_time=utc_now_iso(),
        result=result,
        evidence={
            "registry_writer_confirmed": confirmed,
            "writer_evidence_count": len(writer.get("writer_evidence") or []),
        },
        limitations=["Sysmon E13 required for writer proof — not assumed."],
    )


def _test_tls_trust(fixture: dict[str, Any]) -> ControlTestExecution:
    tls = fixture.get("tls_proof") or {}
    if not tls:
        return ControlTestExecution(
            test_id=f"TST-{uuid.uuid4().hex[:8]}",
            control_id="NET-003",
            control_name="TLS Trust Path Validation",
            execution_time=utc_now_iso(),
            result=TestResult.NOT_TESTED,
            evidence={"note": "no tls_proof in fixture"},
            limitations=[],
        )
    mismatch = tls.get("certificate_mismatch", False)
    return ControlTestExecution(
        test_id=f"TST-{uuid.uuid4().hex[:8]}",
        control_id="NET-003",
        control_name="TLS Trust Path Validation",
        execution_time=utc_now_iso(),
        result=TestResult.FAIL if mismatch else TestResult.PASS,
        evidence={
            "certificate_mismatch": mismatch,
            "mitm_risk_level": tls.get("mitm_risk_level"),
            "mismatch_fields": tls.get("mismatch_fields", []),
        },
        limitations=list(tls.get("limitations") or [
            "Certificate contrast is not definitive MITM proof.",
        ]),
    )


def _test_remediation_gate(fixture: dict[str, Any]) -> ControlTestExecution:
    policy = fixture.get("policy_decision") or {}
    dry_run = fixture.get("dry_run", True) or policy.get("dry_run", True)
    requires = policy.get("requires_confirmation", True)
    passed = dry_run and requires
    return ControlTestExecution(
        test_id=f"TST-{uuid.uuid4().hex[:8]}",
        control_id="NET-004",
        control_name="Remediation Preview Gate",
        execution_time=utc_now_iso(),
        result=TestResult.PASS if passed else TestResult.FAIL,
        evidence={
            "dry_run": dry_run,
            "requires_confirmation": requires,
            "outcome": policy.get("outcome"),
        },
        limitations=["Policy permission is not a safety guarantee."],
    )


_RUNNERS = {
    "NET-001": _test_proxy_baseline,
    "NET-002": _test_registry_integrity,
    "NET-003": _test_tls_trust,
    "NET-004": _test_remediation_gate,
}


def run_control_tests(fixture: dict[str, Any]) -> list[ControlTestExecution]:
    classification = (fixture.get("classification") or {}).get("primary_classification", "NO_PROXY")
    controls = controls_for_classification(classification)
    results: list[ControlTestExecution] = []
    for ctrl in controls:
        runner = _RUNNERS.get(ctrl.control_id)
        if runner:
            results.append(runner(fixture))
        else:
            results.append(
                ControlTestExecution(
                    test_id=f"TST-{uuid.uuid4().hex[:8]}",
                    control_id=ctrl.control_id,
                    control_name=ctrl.control_name,
                    execution_time=utc_now_iso(),
                    result=TestResult.NOT_TESTED,
                    evidence={"note": "no automated runner for control"},
                )
            )
    return results

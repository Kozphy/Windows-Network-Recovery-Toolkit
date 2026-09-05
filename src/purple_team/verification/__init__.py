"""Independent post-condition verification — command success ≠ recovered."""

from __future__ import annotations

from typing import Any

from src.purple_team.models import (
    RemediationOutcome,
    ScenarioDefinition,
    VerificationResult,
)


def _check_proxy_baseline(fixture: dict[str, Any]) -> dict[str, Any]:
    expected = dict(fixture.get("baseline_state") or {})
    actual = dict(
        fixture.get("remediated_state")
        or fixture.get("post_state")
        or fixture.get("observed_state")
        or {}
    )
    # Prefer remediated_state when present.
    if "remediated_state" in fixture:
        actual = dict(fixture["remediated_state"])
    ok = actual == expected and bool(expected)
    return {
        "condition": "proxy_state_matches_baseline",
        "passed": ok,
        "expected": expected,
        "actual": actual,
        "command_success_alone": bool(fixture.get("remediation_command_success")),
    }


def _check_views_reconciled(fixture: dict[str, Any]) -> dict[str, Any]:
    state = dict(fixture.get("remediated_state") or fixture.get("post_state") or {})
    ok = state.get("wininet_proxy") == state.get("winhttp_proxy")
    return {
        "condition": "winhttp_wininet_reconciled",
        "passed": ok,
        "actual": state,
    }


def _check_endpoint_healthy(fixture: dict[str, Any]) -> dict[str, Any]:
    state = dict(fixture.get("remediated_state") or fixture.get("post_state") or {})
    ok = str(state.get("state") or "").lower() == "healthy"
    return {
        "condition": "endpoint_state_healthy",
        "passed": ok,
        "actual": state,
    }


def _check_tls_expected(fixture: dict[str, Any]) -> dict[str, Any]:
    state = dict(fixture.get("remediated_state") or fixture.get("post_state") or {})
    ok = state.get("path_class") == "expected"
    return {
        "condition": "tls_path_expected",
        "passed": ok,
        "actual": state,
    }


def _check_no_high_severity(fixture: dict[str, Any], detections_fired: bool) -> dict[str, Any]:
    return {
        "condition": "no_high_severity_alert",
        "passed": not detections_fired,
        "detections_fired": detections_fired,
    }


_PREDICATES = {
    "proxy_state_matches_baseline": _check_proxy_baseline,
    "winhttp_wininet_reconciled": _check_views_reconciled,
    "endpoint_state_healthy": _check_endpoint_healthy,
    "tls_path_expected": _check_tls_expected,
}


def verify(
    scenario: ScenarioDefinition,
    fixture: dict[str, Any],
    remediation: RemediationOutcome | None,
    *,
    detections_fired: bool,
    skip_verification: bool = False,
) -> VerificationResult:
    if skip_verification:
        # Ablation: pretend pass from command success — used only to measure harm of skipping.
        cmd_ok = bool(remediation and remediation.success)
        return VerificationResult(
            passed=cmd_ok,
            post_conditions=[{"condition": "ablation_skip", "passed": cmd_ok}],
            recovered=cmd_ok,
            limitations=["Verification disabled by ablation — unsafe for production claims."],
        )

    results: list[dict[str, Any]] = []
    for cond in scenario.verification.post_conditions:
        if cond == "no_high_severity_alert":
            results.append(_check_no_high_severity(fixture, detections_fired))
            continue
        fn = _PREDICATES.get(cond)
        if fn is None:
            results.append({"condition": cond, "passed": False, "error": "unknown_predicate"})
            continue
        results.append(fn(fixture))

    passed = all(bool(r.get("passed")) for r in results) if results else False
    # Invariant: verification failure cannot report recovered.
    recovered = passed
    limitations = [
        "Independent post-conditions evaluated against fixture state.",
        "remediation_command_success is insufficient without post-condition match.",
    ]
    if remediation and remediation.details.get("command_success") and not passed:
        limitations.append("Command reported success but post-conditions failed — not recovered.")
    return VerificationResult(
        passed=passed,
        post_conditions=results,
        recovered=recovered,
        limitations=limitations,
    )

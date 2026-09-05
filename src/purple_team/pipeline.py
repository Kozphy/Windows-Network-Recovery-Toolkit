"""End-to-end purple scenario pipeline with explicit state machine."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from src.purple_team.detection import run_detection
from src.purple_team.evaluation import accumulate_metrics, error_analysis_report
from src.purple_team.evidence import build_evidence_bundle, write_evidence_bundle
from src.purple_team.models import (
    FailureCategory,
    RunState,
    ScenarioDefinition,
    ScenarioRunResult,
    StageTiming,
)
from src.purple_team.models.scenario_schema import load_all_scenarios, load_scenario_file
from src.purple_team.response import recommend, remediate_fixture
from src.purple_team.risk import score_risk
from src.purple_team.safety import evaluate_safety
from src.purple_team.simulation import simulate_from_fixture
from src.purple_team.verification import verify


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _transition(transitions: list[dict[str, Any]], state: RunState) -> RunState:
    transitions.append({"state": state.value, "ts": time.time()})
    return state


def run_scenario(
    scenario: ScenarioDefinition,
    *,
    dry_run: bool = True,
    authorized: bool = False,
    approved: bool = False,
    environment: str = "fixture",
    evidence_dir: Path | None = None,
    ablation: dict[str, bool] | None = None,
) -> ScenarioRunResult:
    """Execute one scenario through the purple lifecycle (fixture-only)."""
    ablation = dict(ablation or {})
    run_id = str(uuid.uuid4())
    transitions: list[dict[str, Any]] = []
    timing = StageTiming()
    limitations: list[str] = list(scenario.limitations)
    state = _transition(transitions, RunState.CREATED)

    state = _transition(transitions, RunState.VALIDATING)
    decision = evaluate_safety(
        scenario,
        dry_run=dry_run,
        authorized=authorized,
        environment=environment,
    )
    limitations.extend(decision.limitations)

    if not decision.allowed:
        state = _transition(transitions, RunState.DENIED)
        return ScenarioRunResult(
            run_id=run_id,
            scenario_id=scenario.id,
            state=state,
            dry_run=dry_run,
            authorized=authorized,
            transitions=transitions,
            telemetry=[],
            detections=[],
            risk=None,
            recommendation=None,
            remediation=None,
            verification=None,
            timing=timing,
            failure_category=FailureCategory.SAFETY_DENIED,
            error=";".join(decision.reasons),
            expected_detection=scenario.expect_detection,
            detection_matched_expectation=False,
            true_positive=False,
            false_positive=False,
            true_negative=False,
            false_negative=False,
            evidence_bundle_path=None,
            limitations=limitations,
            ablation=ablation,
        )

    state = _transition(transitions, RunState.AUTHORIZED)
    root = repo_root()

    state = _transition(transitions, RunState.SIMULATING)
    timing.t0_simulation_start = time.perf_counter()
    try:
        fixture, events = simulate_from_fixture(scenario, run_id=run_id, repo_root=root)
    except Exception as exc:  # noqa: BLE001 — captured into run result
        state = _transition(transitions, RunState.FAILED)
        return ScenarioRunResult(
            run_id=run_id,
            scenario_id=scenario.id,
            state=state,
            dry_run=dry_run,
            authorized=authorized,
            transitions=transitions,
            telemetry=[],
            detections=[],
            risk=None,
            recommendation=None,
            remediation=None,
            verification=None,
            timing=timing,
            failure_category=FailureCategory.SIMULATION_FAILURE,
            error=str(exc),
            expected_detection=scenario.expect_detection,
            detection_matched_expectation=False,
            true_positive=False,
            false_positive=False,
            true_negative=False,
            false_negative=False,
            evidence_bundle_path=None,
            limitations=limitations,
            ablation=ablation,
        )

    timing.t1_telemetry_generated = time.perf_counter()
    state = _transition(transitions, RunState.COLLECTING)
    timing.t2_telemetry_collected = time.perf_counter()

    state = _transition(transitions, RunState.DETECTING)
    disable_rules = set()
    if ablation.get("disable_rules"):
        disable_rules.add(scenario.expected_detection)
    detections = run_detection(
        scenario,
        events,
        disable_rules=disable_rules,
        disable_correlation=bool(ablation.get("disable_correlation")),
    )
    timing.t3_detection_fires = time.perf_counter()

    state = _transition(transitions, RunState.CLASSIFYING)
    risk = score_risk(scenario, detections)
    timing.t4_classification_complete = time.perf_counter()

    state = _transition(transitions, RunState.RESPONDING)
    recommendation = recommend(scenario, detections)
    timing.t5_remediation_starts = time.perf_counter()
    remediation = remediate_fixture(
        scenario,
        fixture,
        recommendation,
        dry_run=dry_run,
        approved=approved or (environment == "ci" and not dry_run),
    )
    timing.t6_remediation_completes = time.perf_counter()

    state = _transition(transitions, RunState.VERIFYING)
    fired = any(d.detected for d in detections)
    # For dry-run suspicious scenarios, verification checks expected post-remediation
    # fixture fields when present; otherwise evaluate benign/no-alert conditions.
    if dry_run and scenario.expect_detection and "baseline_state" in fixture:
        # Preview verification against declared baseline without claiming execution.
        fixture = dict(fixture)
        fixture.setdefault("remediated_state", fixture["baseline_state"])
    verification = verify(
        scenario,
        fixture,
        remediation,
        detections_fired=fired,
        skip_verification=bool(ablation.get("skip_verification")),
    )
    timing.t7_verification_completes = time.perf_counter()

    state = _transition(transitions, RunState.MEASURING)
    expected = scenario.expect_detection
    tp = bool(expected and fired)
    fp = bool((not expected) and fired)
    tn = bool((not expected) and (not fired))
    fn = bool(expected and (not fired))
    matched = (expected and fired) or ((not expected) and (not fired))

    failure = FailureCategory.NONE
    if fp:
        failure = FailureCategory.DETECTION_FALSE_POSITIVE
    elif fn:
        failure = FailureCategory.DETECTION_FALSE_NEGATIVE
    elif verification and not verification.passed and not dry_run:
        failure = FailureCategory.VERIFICATION_FAILURE

    result = ScenarioRunResult(
        run_id=run_id,
        scenario_id=scenario.id,
        state=RunState.COMPLETED,
        dry_run=dry_run,
        authorized=authorized,
        transitions=transitions,
        telemetry=events,
        detections=detections,
        risk=risk,
        recommendation=recommendation,
        remediation=remediation,
        verification=verification,
        timing=timing,
        failure_category=failure,
        error=None,
        expected_detection=expected,
        detection_matched_expectation=matched,
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        evidence_bundle_path=None,
        limitations=limitations,
        ablation=ablation,
    )
    _transition(transitions, RunState.COMPLETED)

    if evidence_dir is not None:
        bundle = build_evidence_bundle(
            result,
            pre_state=dict(fixture.get("pre_state") or {}),
            simulation_evidence={
                "action": scenario.simulation.action,
                "fixture_path": scenario.simulation.fixture_path,
            },
        )
        out = evidence_dir / f"{scenario.id}_{run_id}.json"
        write_evidence_bundle(bundle, out)
        result.evidence_bundle_path = str(out)

    return result


def dry_run_preview(scenario: ScenarioDefinition) -> dict[str, Any]:
    """Preview actions/evidence/rollback/detection without changing the machine."""
    decision = evaluate_safety(scenario, dry_run=True, authorized=False, environment="fixture")
    return {
        "scenario_id": scenario.id,
        "title": scenario.title,
        "dry_run": True,
        "safety": decision.to_dict(),
        "actions_that_would_occur": [
            f"load fixture {scenario.simulation.fixture_path}",
            f"simulate action {scenario.simulation.action}",
            "normalize telemetry",
            f"evaluate rule {scenario.expected_detection}",
            f"recommend {scenario.expected_response}",
            "verify post-conditions (preview)",
        ],
        "evidence_expected": list(scenario.expected_telemetry),
        "rollback_plan": list(scenario.cleanup.steps),
        "detection_expected": scenario.expected_detection,
        "expect_detection": scenario.expect_detection,
        "risk_level": scenario.risk_level,
        "verification_criteria": list(scenario.verification.post_conditions),
        "limitations": decision.limitations,
    }


def run_benchmark(
    *,
    scenarios: list[ScenarioDefinition] | None = None,
    dry_run: bool = True,
    authorized: bool = True,
    evidence_dir: Path | None = None,
    ablation: dict[str, bool] | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    scenarios = scenarios or load_all_scenarios()
    if category:
        scenarios = [s for s in scenarios if s.category == category]
    results = [
        run_scenario(
            s,
            dry_run=dry_run,
            authorized=authorized,
            approved=True,
            environment="ci" if dry_run else "lab",
            evidence_dir=evidence_dir,
            ablation=ablation,
        )
        for s in scenarios
    ]
    metrics = accumulate_metrics(results)
    return {
        "schema_version": "purple_benchmark.v1",
        "n_scenarios": len(scenarios),
        "dry_run": dry_run,
        "ablation": ablation or {},
        "metrics": metrics,
        "error_analysis": error_analysis_report(results),
        "results": [r.to_dict() for r in results],
        "limitations": [
            "Metrics are computed from fixture scenario executions only.",
            "Do not extrapolate to fleet MTTD or production SOC SLAs.",
        ],
    }


def load_scenario_by_id(scenario_id: str) -> ScenarioDefinition:
    for path in (repo_root() / "scenarios").glob("*"):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        scen = load_scenario_file(path)
        if scen.id == scenario_id:
            return scen
    raise FileNotFoundError(f"scenario not found: {scenario_id}")

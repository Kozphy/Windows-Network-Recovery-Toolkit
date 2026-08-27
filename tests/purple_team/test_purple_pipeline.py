"""Purple Team foundation tests — fixture-only, no live host mutation."""

from __future__ import annotations

import pytest

from src.purple_team.detection import RULE_REGISTRY, run_detection
from src.purple_team.evidence import build_evidence_bundle, verify_evidence_bundle
from src.purple_team.models import RemediationOutcome
from src.purple_team.models.scenario_schema import (
    ScenarioSchemaError,
    load_all_scenarios,
    validate_raw_scenario,
)
from src.purple_team.pipeline import (
    dry_run_preview,
    load_scenario_by_id,
    repo_root,
    run_benchmark,
    run_scenario,
)
from src.purple_team.safety import evaluate_safety
from src.purple_team.simulation import simulate_from_fixture
from src.purple_team.verification import verify


def test_load_five_scenarios():
    scenarios = load_all_scenarios()
    assert len(scenarios) >= 5
    ids = {s.id for s in scenarios}
    assert "proxy-drift-001" in ids
    assert "benign-admin-001" in ids


def test_reject_missing_cleanup():
    raw = {
        "id": "bad",
        "title": "bad",
        "category": "x",
        "risk_level": "low",
        "safe_for_local_execution": True,
        "preconditions": ["fixture_only"],
        "simulation": {"action": "x", "fixture_path": "y"},
        "expected_telemetry": ["a"],
        "expected_detection": "DET-PROXY-001",
        "expected_response": "observe",
        "verification": {"post_conditions": ["proxy_state_matches_baseline"]},
        "cleanup": {"required": False, "steps": []},
    }
    with pytest.raises(ScenarioSchemaError):
        validate_raw_scenario(raw)


def test_reject_remote_target():
    raw = {
        "id": "bad-remote",
        "title": "bad",
        "category": "x",
        "risk_level": "low",
        "safe_for_local_execution": True,
        "preconditions": ["fixture_only"],
        "simulation": {"action": "x", "fixture_path": "y"},
        "expected_telemetry": ["a"],
        "expected_detection": "DET-PROXY-001",
        "expected_response": "observe",
        "verification": {"post_conditions": ["proxy_state_matches_baseline"]},
        "cleanup": {"required": True, "steps": ["rollback"]},
        "allows_remote_target": True,
    }
    with pytest.raises(ScenarioSchemaError):
        validate_raw_scenario(raw)


def test_safety_denies_unauthorized_non_dry_run():
    scen = load_scenario_by_id("proxy-drift-001")
    decision = evaluate_safety(scen, dry_run=False, authorized=False, environment="lab")
    assert decision.allowed is False


def test_dry_run_preview_allowed():
    scen = load_scenario_by_id("proxy-drift-001")
    preview = dry_run_preview(scen)
    assert preview["dry_run"] is True
    assert preview["safety"]["allowed"] is True
    assert "rollback_plan" in preview


def test_proxy_drift_true_positive():
    scen = load_scenario_by_id("proxy-drift-001")
    result = run_scenario(scen, dry_run=True, authorized=False, environment="fixture")
    assert result.true_positive is True
    assert result.false_positive is False
    assert any(d.detected for d in result.detections)
    assert result.detections[0].rule_id == "DET-PROXY-001"


def test_benign_admin_true_negative():
    scen = load_scenario_by_id("benign-admin-001")
    result = run_scenario(scen, dry_run=True, authorized=False, environment="fixture")
    assert result.true_negative is True
    assert result.false_positive is False
    assert not any(d.detected for d in result.detections)


def test_positive_and_negative_rules_exist():
    assert "DET-PROXY-001" in RULE_REGISTRY
    assert "DET-BENIGN-001" in RULE_REGISTRY
    scen = load_scenario_by_id("proxy-drift-001")
    _, events = simulate_from_fixture(scen, run_id="t", repo_root=repo_root())
    pos = run_detection(scen, events)
    assert pos[0].detected is True
    benign = load_scenario_by_id("benign-admin-001")
    _, bevents = simulate_from_fixture(benign, run_id="t2", repo_root=repo_root())
    neg = run_detection(benign, bevents)
    assert neg[0].detected is False


def test_verification_failure_not_recovered():
    scen = load_scenario_by_id("proxy-drift-001")
    fixture = {
        "baseline_state": {"ProxyEnable": 0},
        "remediated_state": {"ProxyEnable": 1},
        "remediation_command_success": True,
    }
    rem = RemediationOutcome(
        recommended=True,
        executed=True,
        success=True,
        dry_run=False,
        details={"command_success": True},
        limitations=[],
    )
    ver = verify(scen, fixture, rem, detections_fired=True)
    assert ver.passed is False
    assert ver.recovered is False
    assert ver.to_dict()["recovered"] is False


def test_evidence_tamper_detection():
    scen = load_scenario_by_id("proxy-drift-001")
    result = run_scenario(scen, dry_run=True, authorized=False)
    bundle = build_evidence_bundle(
        result,
        pre_state={"ProxyEnable": 0},
        simulation_evidence={"action": "x"},
    )
    assert verify_evidence_bundle(bundle)["ok"] is True
    bundle["records"][0]["payload"] = {"tampered": True}
    assert verify_evidence_bundle(bundle)["ok"] is False


def test_benchmark_computes_confusion():
    report = run_benchmark(dry_run=True, authorized=True, evidence_dir=None)
    conf = report["metrics"]["confusion"]
    assert conf["tp"] >= 4
    assert conf["tn"] >= 1
    assert conf["fp"] == 0
    assert conf["fn"] == 0
    assert conf["precision"] == 1.0
    assert conf["recall"] == 1.0
    assert "median_mttd_s" in report["metrics"]["operational"]


def test_ablation_minus_rules_causes_fn():
    report = run_benchmark(
        dry_run=True,
        authorized=True,
        evidence_dir=None,
        ablation={"disable_rules": True},
    )
    assert report["metrics"]["confusion"]["fn"] >= 1


def test_mttd_measurable():
    scen = load_scenario_by_id("proxy-drift-001")
    result = run_scenario(scen, dry_run=True)
    timing = result.timing.to_dict()
    assert timing["mttd_s"] is not None
    assert timing["mttd_s"] >= 0.0

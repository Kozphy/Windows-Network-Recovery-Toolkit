"""Edge reasoning + policy guarantees (deterministic, simulation-only).

Verifies the AI-edge reliability layer enforces the same epistemic and safety contract as
the existing endpoint engine:
    * destructive actions are never allowed,
    * high confidence without proof stays PREVIEW,
    * confirmed safe remediation reaches ALLOW only for low-risk actions,
    * no non-cataloged (fabricated) root cause is emitted,
    * runs are deterministic and replayable from append-only JSONL.
"""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.reasoning_models import ProofResult
from edge_device.audit import append_edge_run, load_edge_run
from edge_device.policy import EDGE_SAFE_ACTIONS
from edge_device.reasoning import run_edge_reasoning
from edge_device.scenarios import EDGE_SCENARIOS, NOMINAL_HYPOTHESIS
from edge_device.simulator import SIM_PROFILES, simulate_edge_observations

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "edge"

_CATALOG_IDS = {s.id for s in EDGE_SCENARIOS}
_ALLOWED_ACCEPTED = _CATALOG_IDS | {NOMINAL_HYPOTHESIS, "edge_state_indeterminate"}


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _run_fixture(name: str):
    blob = _load(name)
    proof = blob.get("proof")
    proof_result = (
        ProofResult(
            hypothesis=str(proof.get("hypothesis") or ""),
            status=str(proof.get("status") or "NOT_RUN"),
            checks_run=list(proof.get("checks_run") or []),
        )
        if isinstance(proof, dict)
        else None
    )
    return run_edge_reasoning(
        dict(blob.get("observations") or {}),
        device_profile=dict(blob.get("device_profile") or {}),
        proof_result=proof_result,
        requested_action=blob.get("requested_action"),
        explicit_confirmation=bool(blob.get("explicit_confirmation", False)),
    )


def test_destructive_action_is_always_blocked() -> None:
    for action in ("flash_firmware", "disable_thermal_protection", "force_overclock", "factory_reset"):
        run = run_edge_reasoning(
            _load("thermal_throttle.json")["observations"],
            requested_action=action,
        )
        assert run.policy_decision.outcome == "BLOCK"
        # The action must never appear as an authorized safe action.
        assert action not in EDGE_SAFE_ACTIONS


def test_blocked_actions_always_listed_even_on_preview() -> None:
    run = _run_fixture("thermal_throttle.json")
    blocked = set(run.policy_decision.blocked_actions)
    assert {"flash_firmware", "factory_reset", "force_overclock"} <= blocked


def test_high_confidence_without_proof_stays_preview() -> None:
    # Thermal fixture has strong supporting signals but no CONFIRMED proof and a safe action.
    run = run_edge_reasoning(
        _load("thermal_throttle.json")["observations"],
        requested_action="reduce_inference_load",
        explicit_confirmation=True,  # confirmation present, but proof is NOT_RUN
    )
    assert run.proof_result.status != "CONFIRMED"
    assert run.policy_decision.outcome == "PREVIEW"
    assert "HIGH_CONFIDENCE_UNPROVEN" in run.policy_decision.reason_codes


def test_confirmed_safe_action_reaches_allow_for_low_risk() -> None:
    run = _run_fixture("latency_regression.json")  # CONFIRMED proof + explicit_confirmation + safe action
    assert run.proof_result.status == "CONFIRMED"
    assert run.policy_decision.requested_action in EDGE_SAFE_ACTIONS
    assert run.policy_decision.outcome == "ALLOW"


def test_confirmed_but_non_safe_action_is_blocked() -> None:
    blob = _load("latency_regression.json")
    run = run_edge_reasoning(
        blob["observations"],
        proof_result=ProofResult(hypothesis="edge_inference_latency_regression", status="CONFIRMED"),
        requested_action="recalibrate_npu_scheduler",  # not allowlisted, not destructive
        explicit_confirmation=True,
    )
    assert run.policy_decision.outcome == "BLOCK"
    assert "UNKNOWN_ACTION" in run.policy_decision.reason_codes


def test_no_action_is_diagnostic_preview() -> None:
    run = _run_fixture("sensor_degraded.json")
    assert run.policy_decision.outcome == "PREVIEW"
    assert "DIAGNOSTIC_ONLY" in run.policy_decision.reason_codes


def test_healthy_device_emits_no_fabricated_root_cause() -> None:
    run = _run_fixture("healthy.json")
    assert run.accepted_hypothesis == NOMINAL_HYPOTHESIS
    assert run.accepted_hypothesis not in _CATALOG_IDS
    assert run.reliability_impact.severity == "low"


def test_only_cataloged_hypotheses_are_ever_accepted() -> None:
    for name in (
        "thermal_throttle.json",
        "npu_fallback.json",
        "latency_regression.json",
        "driver_mismatch.json",
        "sensor_degraded.json",
        "uplink_degraded_local_ok.json",
        "healthy.json",
    ):
        run = _run_fixture(name)
        assert run.accepted_hypothesis in _ALLOWED_ACCEPTED


def test_expected_accepted_hypothesis_per_fixture() -> None:
    expectations = {
        "thermal_throttle.json": "thermal_throttling_risk",
        "npu_fallback.json": "npu_fallback_to_cpu",
        "latency_regression.json": "edge_inference_latency_regression",
        "driver_mismatch.json": "driver_runtime_mismatch",
        "sensor_degraded.json": "sensor_input_degraded",
        "uplink_degraded_local_ok.json": "uplink_degraded_but_local_inference_ok",
    }
    for name, expected in expectations.items():
        run = _run_fixture(name)
        assert run.accepted_hypothesis == expected, f"{name}: {run.accepted_hypothesis}"


def test_uplink_degraded_keeps_low_impact_when_local_ok() -> None:
    run = _run_fixture("uplink_degraded_local_ok.json")
    assert run.accepted_hypothesis == "uplink_degraded_but_local_inference_ok"
    assert run.reliability_impact.severity == "low"
    assert run.normalized_signals["local_inference_ok"] is True


def test_confidence_is_capped_without_proof() -> None:
    run = _run_fixture("driver_mismatch.json")
    top = run.hypothesis_ranking[0]["confidence"]
    assert 0.0 <= top <= 0.9  # unproven cap


def test_evidence_sections_present_in_output() -> None:
    out = _run_fixture("npu_fallback.json").to_output_dict()
    for key in (
        "observed_signals",
        "inferred_hypotheses",
        "supporting_evidence",
        "contradicting_evidence",
        "missing_evidence",
        "proof_status",
        "policy_decision",
        "safe_next_action",
        "blocked_actions",
    ):
        assert key in out


def test_determinism_same_inputs_same_decision() -> None:
    obs = _load("thermal_throttle.json")["observations"]
    a = run_edge_reasoning(obs, requested_action="reduce_inference_load")
    b = run_edge_reasoning(obs, requested_action="reduce_inference_load")
    assert a.accepted_hypothesis == b.accepted_hypothesis
    assert a.policy_decision.outcome == b.policy_decision.outcome
    assert a.policy_decision.reason_codes == b.policy_decision.reason_codes
    assert a.hypothesis_ranking == b.hypothesis_ranking


def test_append_and_replay_roundtrip(tmp_path: Path) -> None:
    run = _run_fixture("thermal_throttle.json")
    append_edge_run(tmp_path, run)
    loaded = load_edge_run(tmp_path, run.id)
    assert loaded is not None
    assert loaded["run_id"] == run.id
    assert loaded["accepted_hypothesis"] == run.accepted_hypothesis
    assert loaded["policy_decision"]["decision"] == run.policy_decision.outcome
    assert load_edge_run(tmp_path, "nonexistent-run-id") is None


def test_simulated_profiles_are_deterministic_and_safe() -> None:
    for profile in SIM_PROFILES:
        a = simulate_edge_observations(profile=profile)
        b = simulate_edge_observations(profile=profile)
        assert a == b  # deterministic
        run = run_edge_reasoning(a)
        # No requested action -> diagnostic-only preview, never ALLOW/BLOCK from simulation alone.
        assert run.policy_decision.outcome == "PREVIEW"

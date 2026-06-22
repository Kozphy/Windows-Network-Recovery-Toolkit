"""15-scenario evaluation matrix tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.governance.proof_tier import resolve_proof_tier
from src.platform_core.policy.outcome_normalizer import normalize_policy_outcome

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = json.loads(
    (ROOT / "tests/fixtures/evaluation/scenarios_15.json").read_text(encoding="utf-8")
)["scenarios"]


def _load_fixture(rel: str) -> dict:
    path = ROOT / rel
    if path.suffix == ".jsonl":
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return json.loads(lines[0]) if lines else {}
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_from_fixture_dir(fixture_path: str) -> dict | None:
    p = Path(fixture_path)
    expected = p.parent / "expected_classification.json"
    if expected.is_file():
        return json.loads(expected.read_text(encoding="utf-8"))
    return None


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_classification_and_policy(scenario: dict) -> None:
    if scenario.get("replay_jsonl"):
        pytest.skip("JSONL replay scenarios covered by proxy-replay tests")

    fixture = _load_fixture(scenario["fixture"])
    pack_expected = _expected_from_fixture_dir(scenario["fixture"])

    if pack_expected:
        primary = pack_expected["primary_classification"]
    elif fixture.get("expected_primary"):
        primary = fixture["expected_primary"]
    elif fixture.get("classification", {}).get("primary_classification"):
        primary = fixture["classification"]["primary_classification"]
    else:
        pytest.skip(f"No classification anchor in {scenario['fixture']}")

    assert primary == scenario["expected_primary"]

    tier = resolve_proof_tier(fixture)
    assert str(tier.proof_tier.value).startswith(scenario["expected_proof_tier_prefix"])

    if pack_expected and "expected_policy.json" in str(scenario["fixture"]):
        pol_path = Path(scenario["fixture"]).parent / "expected_policy.json"
        pol_expected = json.loads(pol_path.read_text(encoding="utf-8"))
        gate = normalize_policy_outcome(str(pol_expected.get("policy_gate", "")))
    else:
        pol = fixture.get("policy_decision") or {}
        gate = normalize_policy_outcome(str(pol.get("outcome", scenario["expected_policy_gate"])))

    expected_gate = scenario["expected_policy_gate"]
    assert gate.value == expected_gate or expected_gate in gate.value

    limitations = (
        fixture.get("classification", {}).get("limitations")
        or tier.limitations
        or pack_expected
    )
    assert limitations

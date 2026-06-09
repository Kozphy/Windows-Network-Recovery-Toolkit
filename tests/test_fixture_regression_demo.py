"""Fixture regression — all demo scenarios deterministic on Linux CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from src.demo_handlers import SCENARIOS, cmd_demo_scenario, run_demo_scenario

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
def test_demo_scenario_cli_exits_zero(name: str) -> None:
    code = cmd_demo_scenario(
        argparse.Namespace(demo_scenario=name, demo_format="json", repo_root=str(REPO))
    )
    assert code == 0


@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
def test_evidence_and_policy_match_fixture_expectations(name: str) -> None:
    report = run_demo_scenario(name, repo_root=REPO)
    assert report["evidence_level"] == report["expected_evidence_level"]
    assert report["policy_decision"] == report["expected_policy"]


@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
def test_json_report_roundtrip_stable(name: str) -> None:
    report = run_demo_scenario(name, repo_root=REPO)
    encoded = json.dumps(report, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["fingerprint"] == report["fingerprint"]


def test_fleet_100_endpoints_20_incidents(tmp_path) -> None:
    from platform_core.fleet_simulation import run_fleet_simulation

    summary = run_fleet_simulation(
        scenario="enterprise-mix",
        endpoints=100,
        incidents=20,
        repo_root=REPO,
        out_dir=tmp_path,
    )
    assert summary["endpoints"] == 100
    assert summary["incidents_total"] == 20
    lines = (tmp_path / "endpoints.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 100

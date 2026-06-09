"""Fixture regression — all demo scenarios deterministic on Linux CI."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.demo_handlers import SCENARIOS, cmd_demo_scenario
import argparse

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
def test_demo_scenario_cli_exits_zero(name: str) -> None:
    code = cmd_demo_scenario(
        argparse.Namespace(demo_scenario=name, demo_format="json", repo_root=str(REPO))
    )
    assert code == 0


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

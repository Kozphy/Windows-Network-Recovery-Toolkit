"""Fleet simulation tests — writes only under tmp_path."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.fleet_simulation import fleet_report, run_fleet_simulation


def test_fleet_simulate_proxy_drift(tmp_path) -> None:
    repo = Path(__file__).resolve().parents[1]
    out = tmp_path / "fleet_demo"
    summary = run_fleet_simulation(
        scenario="proxy-drift",
        endpoints=25,
        repo_root=repo,
        out_dir=out,
    )
    assert summary["endpoints"] == 25
    assert summary["proxy_drift_incidents"] == 5
    assert (out / "endpoints.jsonl").is_file()
    assert (out / "failure_events.jsonl").is_file()
    lines = (out / "endpoints.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 25


def test_fleet_report_reads_summary(tmp_path) -> None:
    repo = Path(__file__).resolve().parents[1]
    out = tmp_path / "fleet_demo"
    run_fleet_simulation(scenario="proxy-drift", endpoints=10, repo_root=repo, out_dir=out)
    report = fleet_report(repo_root=repo, out_dir=out)
    assert report["endpoints"] == 10


def test_cli_fleet_simulate() -> None:
    import argparse
    import tempfile

    from src.production_handlers import cmd_fleet_simulate

    with tempfile.TemporaryDirectory() as td:
        repo = Path(__file__).resolve().parents[1]
        code = cmd_fleet_simulate(
            argparse.Namespace(
                fleet_scenario="proxy-drift",
                fleet_endpoints=5,
                repo_root=str(repo),
            )
        )
        assert code == 0

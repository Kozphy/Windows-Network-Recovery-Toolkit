"""Tests for primary CLI fleet-simulate command."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from windows_network_toolkit.analytics_pipeline import run_endpoint_analytics_pipeline
from windows_network_toolkit.cli import main
from windows_network_toolkit.fleet_simulate import run_fleet_simulate

ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN = ("MALWARE_DETECTED", "MITM_CONFIRMED", "COMPROMISED", "autonomous repair")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fleet_simulate_same_seed_identical_hash(tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    run_fleet_simulate(endpoints=20, seed=42, out_dir=out1)
    run_fleet_simulate(endpoints=20, seed=42, out_dir=out2)
    p1 = out1 / "incidents.jsonl"
    p2 = out2 / "incidents.jsonl"
    assert _file_hash(p1) == _file_hash(p2)
    lines1 = p1.read_text(encoding="utf-8").strip().splitlines()
    lines2 = p2.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines1) == len(lines2)


def test_fleet_simulate_distinct_endpoint_ids(tmp_path: Path) -> None:
    summary = run_fleet_simulate(endpoints=100, seed=42, out_dir=tmp_path)
    assert summary["endpoints"] == 100
    ids: set[str] = set()
    for line in (tmp_path / "incidents.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("endpoint_id"):
            ids.add(row["endpoint_id"])
    assert len(ids) == 100
    assert "endpoint-001" in ids
    assert "endpoint-100" in ids


def test_fleet_simulate_all_incidents_have_limitations(tmp_path: Path) -> None:
    run_fleet_simulate(endpoints=30, seed=7, out_dir=tmp_path)
    for line in (tmp_path / "incidents.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("classification"):
            assert row.get("limitations"), row
            assert len(row["limitations"]) >= 2


def test_fleet_simulate_forbidden_verdicts_absent(tmp_path: Path) -> None:
    run_fleet_simulate(endpoints=50, seed=1, out_dir=tmp_path)
    text = (tmp_path / "incidents.jsonl").read_text(encoding="utf-8").upper()
    for phrase in _FORBIDDEN:
        assert phrase.upper() not in text


def test_fleet_simulate_analytics_pipeline_succeeds(tmp_path: Path) -> None:
    run_fleet_simulate(endpoints=10, seed=99, out_dir=tmp_path)
    payload = run_endpoint_analytics_pipeline(input_path=tmp_path)
    assert payload.get("schema_version") == "endpoint_evidence_analytics.v1"


def test_fleet_simulate_cli_exit_zero(tmp_path: Path) -> None:
    assert (
        main(
            [
                "fleet-simulate",
                "--endpoints",
                "5",
                "--seed",
                "42",
                "--out",
                str(tmp_path / "cli_out"),
            ]
        )
        == 0
    )

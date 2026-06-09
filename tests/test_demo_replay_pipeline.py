"""Replay determinism for Tier-1 demo fixtures (offline, no host mutation)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from platform_core.demo_replay import (
    build_replay_events,
    replay_fixture_blob,
    replay_summary_from_events,
    report_fingerprint,
)
from src.demo_handlers import SCENARIOS, run_demo_scenario

REPO = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO / "tests" / "fixtures" / "demo"

REQUIRED_FIXTURES = (
    "healthy_endpoint.json",
    "proxy_drift_correlated_only.json",
    "sysmon_registry_writer_proven.json",
    "final_causation_browser_path_failure.json",
    "suspicious_external_proxy.json",
    "stale_localhost_proxy_listener.json",
    "developer_tool_proxy_allowed.json",
)

REQUIRED_REPORT_KEYS = (
    "scenario_id",
    "evidence_level",
    "policy_decision",
    "limitations",
    "recommended_next_step",
    "recommended_next_steps",
    "replay",
    "fingerprint",
    "host_mutation",
    "requires_admin",
)


@pytest.mark.parametrize("fname", REQUIRED_FIXTURES)
def test_demo_fixture_file_exists(fname: str) -> None:
    path = DEMO_DIR / fname
    assert path.is_file(), f"missing fixture: {fname}"
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob.get("scenario_id")
    assert blob.get("expected_evidence_level")
    assert blob.get("expected_policy")


@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
def test_demo_report_has_required_fields(name: str) -> None:
    report = run_demo_scenario(name, repo_root=REPO)
    for key in REQUIRED_REPORT_KEYS:
        assert key in report, f"{name} missing {key}"
    assert report["host_mutation"] is False
    assert report["requires_admin"] is False
    assert report["replay"]["replay_stable"] is True


@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
def test_demo_scenario_deterministic_fingerprint(name: str) -> None:
    first = run_demo_scenario(name, repo_root=REPO)
    second = run_demo_scenario(name, repo_root=REPO)
    assert first["fingerprint"] == second["fingerprint"]
    assert first == second


@pytest.mark.parametrize("fname", REQUIRED_FIXTURES)
def test_replay_events_stable_across_runs(fname: str) -> None:
    blob = json.loads((DEMO_DIR / fname).read_text(encoding="utf-8"))
    events_a = build_replay_events(blob)
    events_b = build_replay_events(blob)
    assert events_a == events_b
    summary_a = replay_summary_from_events(events_a)
    summary_b = replay_summary_from_events(events_b)
    assert summary_a == summary_b
    assert summary_a.changed_decisions == 0
    assert summary_a.parse_errors == 0


@pytest.mark.parametrize("fname", REQUIRED_FIXTURES)
def test_replay_fixture_blob_matches_inline_summary(fname: str) -> None:
    blob = json.loads((DEMO_DIR / fname).read_text(encoding="utf-8"))
    replay = replay_fixture_blob(blob)
    assert replay["event_count"] == 1
    assert replay["replay_stable"] is True


def test_demo_scenario_no_subprocess(monkeypatch, name: str = "healthy") -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not be called during fixture demo")

    monkeypatch.setattr("subprocess.run", boom)
    report = run_demo_scenario(name, repo_root=REPO)
    assert report["evidence_level"] == "OBSERVED_ONLY"


def test_report_fingerprint_excludes_self() -> None:
    report = run_demo_scenario("healthy", repo_root=REPO)
    fp = report["fingerprint"]
    copy = dict(report)
    copy["fingerprint"] = "different"
    assert report_fingerprint(copy) == fp


def test_demo_both_format_cli_exits_zero() -> None:
    from src.demo_handlers import cmd_demo_scenario

    code = cmd_demo_scenario(
        argparse.Namespace(demo_scenario="proxy-drift", demo_format="both", repo_root=str(REPO))
    )
    assert code == 0

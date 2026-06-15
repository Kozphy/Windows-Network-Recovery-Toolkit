"""Fleet fixture simulation tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.fleet.simulator import (
    fleet_summary_from_fixture,
    load_fleet_fixture,
    render_fleet_markdown,
    replay_fleet_fixture,
)

REPO = Path(__file__).resolve().parents[1]
FLEET_FIXTURE = REPO / "tests" / "fixtures" / "fleet" / "fleet_100_endpoints.jsonl"


def test_fleet_fixture_has_100_endpoints() -> None:
    rows = load_fleet_fixture(FLEET_FIXTURE)
    assert len(rows) == 100


def test_fleet_summary_classifications() -> None:
    summary = fleet_summary_from_fixture(FLEET_FIXTURE)
    assert summary["total_endpoints"] == 100
    assert summary["total_incidents"] > 0
    assert "DEAD_PROXY_CONFIG" in summary["classifications"]
    assert summary["remediation_preview_count"] > 0


def test_fleet_replay_deterministic() -> None:
    a = replay_fleet_fixture(FLEET_FIXTURE)
    b = replay_fleet_fixture(FLEET_FIXTURE)
    assert a["content_digest"] == b["content_digest"]


def test_fleet_markdown_report() -> None:
    summary = fleet_summary_from_fixture(FLEET_FIXTURE)
    md = render_fleet_markdown(summary)
    assert "# Fleet simulation report" in md
    assert "DEAD_PROXY_CONFIG" in md


def test_cli_fleet_simulate_json(capsys) -> None:
    import argparse

    from windows_network_toolkit.fleet import cmd_fleet_simulate

    code = cmd_fleet_simulate(
        argparse.Namespace(
            fixture=str(FLEET_FIXTURE),
            format="json",
        )
    )
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["total_endpoints"] == 100


def test_cli_fleet_simulate_markdown(capsys) -> None:
    import argparse

    from windows_network_toolkit.fleet import cmd_fleet_simulate

    code = cmd_fleet_simulate(
        argparse.Namespace(
            fixture=str(FLEET_FIXTURE),
            format="markdown",
        )
    )
    assert code == 0
    assert "Fleet simulation report" in capsys.readouterr().out

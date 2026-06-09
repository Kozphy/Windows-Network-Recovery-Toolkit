"""Production demo contract — scripts exist and key commands exit 0."""

from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_demo_production_script_exists() -> None:
    assert (REPO / "scripts" / "demo_production.ps1").is_file()
    assert (REPO / "docs" / "demo_production_5_min.md").is_file()


def test_makefile_demo_production_target() -> None:
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "demo-production" in text


def test_production_demo_command_chain() -> None:
    from src.command_handlers import cmd_proxy_policy
    from src.production_handlers import (
        cmd_fleet_report,
        cmd_fleet_simulate,
        cmd_incident_review,
        cmd_policy_validate,
    )

    assert (
        cmd_incident_review(
            argparse.Namespace(
                incident_id="001_proxy_drift_cursor_node",
                review_format="json",
                repo_root=str(REPO),
            )
        )
        == 0
    )
    assert cmd_policy_validate(argparse.Namespace(policy_path=str(REPO / "config/policies/default.yaml"))) == 0
    assert (
        cmd_fleet_simulate(
            argparse.Namespace(fleet_scenario="proxy-drift", fleet_endpoints=5, repo_root=str(REPO))
        )
        == 0
    )
    assert cmd_fleet_report(argparse.Namespace(fleet_report_format="json", repo_root=str(REPO))) == 0
    assert (
        cmd_proxy_policy(
            argparse.Namespace(
                policy_fixture=str(REPO / "tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json"),
                policy_format="json",
                policy_yaml=str(REPO / "config/policies/strict_enterprise.yaml"),
                policy_input=None,
                emit_json=False,
                repo_root=REPO,
            )
        )
        == 0
    )

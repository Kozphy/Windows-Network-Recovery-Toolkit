"""Tests for cloud governance and FinOps modules (Phase 3)."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.platform_core.cloud_governance import summarize_cloud_recommendations
from src.platform_core.finops import build_finops_export, export_finops
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
CLOUD_FIXTURE = REPO / "tests" / "fixtures" / "cloud_governance" / "mock_recommendations.json"
FINOPS_FIXTURE = REPO / "tests" / "fixtures" / "finops" / "mock_costs.json"


def test_cloud_recommendations_summary() -> None:
    summary = summarize_cloud_recommendations(fixture_path=CLOUD_FIXTURE)
    assert summary["schema_version"] == "cloud_governance_summary.v1"
    assert summary["total_recommendations"] == 5
    assert summary["by_provider"]["azure"] >= 1
    assert summary["governance"]["execution_authority"] == "preview_only"


def test_finops_export_payload() -> None:
    payload = build_finops_export(fixture_path=FINOPS_FIXTURE)
    assert payload["schema_version"] == "finops_export.v1"
    assert len(payload["fact_costs"]) == 5
    assert payload["summary"]["total_monthly_cost_usd"] > 0


def test_finops_export_writes_csv(tmp_path: Path) -> None:
    payload = export_finops(fixture_path=FINOPS_FIXTURE, out_dir=tmp_path, fmt="both")
    assert (tmp_path / "fact_costs.csv").is_file()
    assert (tmp_path / "fact_costs.json").is_file()
    assert payload["csv_path"]


def test_cli_cloud_recommendations_smoke() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "cloud-recommendations",
                "summarize",
                "--fixture",
                str(CLOUD_FIXTURE),
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload["total_recommendations"] == 5


def test_cli_finops_export_smoke(tmp_path: Path) -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "finops",
                "export",
                "--fixture",
                str(FINOPS_FIXTURE),
                "--out-dir",
                str(tmp_path),
                "--format",
                "both",
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload["summary"]["cost_line_count"] == 5

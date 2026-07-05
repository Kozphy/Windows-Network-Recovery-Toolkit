"""Tests for risk matrix export (Phase 1)."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.platform_core.risk.risk_matrix import (
    build_risk_matrix,
    build_risk_matrix_row,
    export_risk_matrix,
)
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "tests" / "fixtures" / "risk_register" / "sample_risk_register.json"


def test_build_risk_matrix_row_has_required_fields() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    row = build_risk_matrix_row(register["risks"][0])
    for field in (
        "risk_id",
        "risk_description",
        "probability_score",
        "impact_score",
        "severity_score",
        "confidence",
        "category",
        "evidence_tier",
        "recommended_control",
        "recommended_action",
        "business_explanation",
    ):
        assert field in row
    assert row["severity_score"] == row["probability_score"] * row["impact_score"]


def test_build_risk_matrix_includes_governance_envelope() -> None:
    payload = build_risk_matrix(register_path=REGISTER)
    assert payload["schema_version"] == "risk_matrix.v1"
    assert payload["governance"]["classification_is_accusation"] is False
    assert len(payload["matrix_rows"]) == 3
    assert payload["limitations"]


def test_export_risk_matrix_csv(tmp_path: Path) -> None:
    out = tmp_path / "risk_matrix.csv"
    payload = export_risk_matrix(register_path=REGISTER, out_path=out, fmt="csv")
    assert out.is_file()
    assert payload["export_format"] == "csv"
    text = out.read_text(encoding="utf-8")
    assert "risk_id" in text
    assert "RISK-001" in text


def test_cli_risk_matrix_export_smoke() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "risk-matrix",
                "export",
                "--register",
                str(REGISTER),
                "--format",
                "json",
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload["schema_version"] == "risk_matrix.v1"

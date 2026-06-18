"""Power BI analytics layer — CSV schema, export, and portfolio sample validation."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.platform_core.analytics.powerbi_export import (
    _INCIDENTS_COLUMNS,
    CONTROL_RESULTS,
    EXECUTION_AUTHORITIES,
    POLICY_DECISIONS,
    PROOF_TIERS,
    RISK_RATINGS,
    export_powerbi_from_audit,
    portfolio_sample_tables,
    write_portfolio_sample,
)
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
PBI_DATA = REPO / "analytics" / "powerbi" / "data"
AUDIT_SAMPLE = REPO / "tests" / "fixtures" / "risk_analytics" / "audit_sample"

CSV_FILES = [
    "incidents.csv",
    "control_tests.csv",
    "audit_events.csv",
    "remediation_previews.csv",
    "risk_decisions.csv",
    "date_dim.csv",
]


@pytest.mark.parametrize("filename", CSV_FILES)
def test_portfolio_csv_files_exist(filename: str) -> None:
    assert (PBI_DATA / filename).is_file()


def test_incidents_required_columns() -> None:
    df = pd.read_csv(PBI_DATA / "incidents.csv")
    for col in _INCIDENTS_COLUMNS:
        assert col in df.columns


def test_date_dim_valid_dates() -> None:
    df = pd.read_csv(PBI_DATA / "date_dim.csv")
    assert "date_key" in df.columns
    assert df["date_key"].between(20200101, 20991231).all()
    parsed = pd.to_datetime(df["full_date"], errors="coerce")
    assert parsed.notna().all()


def test_proof_tier_values_valid() -> None:
    df = pd.read_csv(PBI_DATA / "incidents.csv")
    assert set(df["proof_tier"].dropna()).issubset(PROOF_TIERS)


def test_risk_rating_values_valid() -> None:
    df = pd.read_csv(PBI_DATA / "incidents.csv")
    assert set(df["risk_rating"].dropna()).issubset(RISK_RATINGS)


def test_policy_decision_values_valid() -> None:
    df = pd.read_csv(PBI_DATA / "incidents.csv")
    assert set(df["policy_decision"].dropna()).issubset(POLICY_DECISIONS)


def test_execution_authority_values_valid() -> None:
    df = pd.read_csv(PBI_DATA / "incidents.csv")
    assert set(df["execution_authority"].dropna()).issubset(EXECUTION_AUTHORITIES)


def test_control_test_results_valid() -> None:
    df = pd.read_csv(PBI_DATA / "control_tests.csv")
    assert set(df["control_test_result"].dropna()).issubset(CONTROL_RESULTS)


def test_hash_chain_valid_boolean_compatible() -> None:
    df = pd.read_csv(PBI_DATA / "incidents.csv")
    normalized = df["hash_chain_valid"].map({True: True, False: False, "True": True, "False": False})
    assert normalized.notna().all()


def test_all_sample_csvs_load_with_pandas() -> None:
    for filename in CSV_FILES:
        df = pd.read_csv(PBI_DATA / filename)
        assert len(df) >= 1


def test_portfolio_sample_covers_incident_classes() -> None:
    tables = portfolio_sample_tables()
    classes = {row["classification"] for row in tables["incidents"]}
    expected = {
        "DEAD_PROXY_CONFIG",
        "WININET_WINHTTP_MISMATCH",
        "LOCAL_PROXY_ACTIVE",
        "UNKNOWN_LOCAL_PROXY",
        "PAC_CONFIGURED",
        "POSSIBLE_MITM_RISK",
        "REVERTER_SUSPECTED",
        "ERROR_INSUFFICIENT_DATA",
    }
    assert expected.issubset(classes)


def test_export_from_audit_dir(tmp_path: Path) -> None:
    out = tmp_path / "pbi"
    payload = export_powerbi_from_audit(AUDIT_SAMPLE, out, include_portfolio_seed=True)
    assert payload["command"] == "analytics-export-powerbi"
    for filename in CSV_FILES:
        assert (out / filename).is_file()


def test_cli_analytics_export_powerbi_portfolio_sample(tmp_path: Path) -> None:
    cap = StringIO()
    out = tmp_path / "out"
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "analytics-export-powerbi",
                "--portfolio-sample",
                "--out-dir",
                str(out),
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload["mode"] == "portfolio_sample"
    assert (out / "incidents.csv").is_file()


def test_write_portfolio_sample_idempotent(tmp_path: Path) -> None:
    counts1 = write_portfolio_sample(tmp_path)
    counts2 = write_portfolio_sample(tmp_path)
    assert counts1 == counts2
    assert counts1["incidents"] >= 12

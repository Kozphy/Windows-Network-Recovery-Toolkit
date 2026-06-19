"""Tests for powerbi-export star schema semantic model pack."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform_core.analytics.powerbi_star_export import (
    FACT_CONTROL_TESTS_COLUMNS,
    FACT_INCIDENTS_COLUMNS,
    FACT_POLICY_DECISIONS_COLUMNS,
    STAR_CSV_FILES,
    build_dim_classification,
    build_star_schema_tables,
    export_powerbi_star_schema,
    scan_for_secrets,
)
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
AUDIT_SAMPLE = REPO / "tests" / "fixtures" / "risk_analytics" / "audit_sample"
EXPORT_DIR = REPO / "examples" / "powerbi" / "export"


@pytest.fixture()
def export_dir(tmp_path: Path) -> Path:
    return tmp_path / "export"


def test_powerbi_export_creates_all_required_files(export_dir: Path) -> None:
    payload = export_powerbi_star_schema(AUDIT_SAMPLE, export_dir)
    assert payload["command"] == "powerbi-export"
    for name in STAR_CSV_FILES:
        assert (export_dir / name).is_file()


@pytest.mark.parametrize(
    "filename,columns",
    [
        ("fact_incidents.csv", FACT_INCIDENTS_COLUMNS),
        ("fact_control_tests.csv", FACT_CONTROL_TESTS_COLUMNS),
        ("fact_policy_decisions.csv", FACT_POLICY_DECISIONS_COLUMNS),
    ],
)
def test_csv_required_columns(export_dir: Path, filename: str, columns: list[str]) -> None:
    export_powerbi_star_schema(AUDIT_SAMPLE, export_dir)
    with (export_dir / filename).open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == columns


def test_fact_incidents_stable_incident_ids(export_dir: Path) -> None:
    export_powerbi_star_schema(AUDIT_SAMPLE, export_dir)
    with (export_dir / "fact_incidents.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    ids = [r["incident_id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert all(id_.startswith("INC-") for id_ in ids)


def test_dim_date_valid_date_key_format(export_dir: Path) -> None:
    export_powerbi_star_schema(AUDIT_SAMPLE, export_dir)
    with (export_dir / "dim_date.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = row["date_key"]
            assert len(key) == 8
            assert key.isdigit()
            assert 20200101 <= int(key) <= 20991231


def test_no_secrets_in_export(export_dir: Path) -> None:
    tables = build_star_schema_tables(AUDIT_SAMPLE, include_seed=True)
    assert scan_for_secrets(tables) == []


def test_classification_dimension_not_security_accusation() -> None:
    dim = build_dim_classification()
    assert dim
    assert all(row["is_security_accusation"] is False for row in dim)


def test_export_deterministic_on_same_fixture(export_dir: Path) -> None:
    dir_a = export_dir / "a"
    dir_b = export_dir / "b"
    export_powerbi_star_schema(AUDIT_SAMPLE, dir_a)
    export_powerbi_star_schema(AUDIT_SAMPLE, dir_b)
    for name in STAR_CSV_FILES:
        if not name.endswith(".csv"):
            continue
        assert (dir_a / name).read_text(encoding="utf-8") == (dir_b / name).read_text(encoding="utf-8")


def test_cli_powerbi_export_smoke(export_dir: Path) -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "powerbi-export",
                "--audit-dir",
                str(AUDIT_SAMPLE),
                "--out-dir",
                str(export_dir),
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload["feature"] == "Power BI Risk Analytics Export + Semantic Model Pack"
    assert (export_dir / "fact_incidents.csv").is_file()


@pytest.mark.skipif(not EXPORT_DIR.is_dir(), reason="Committed export folder optional")
def test_committed_export_sample_exists() -> None:
    for name in STAR_CSV_FILES:
        assert (EXPORT_DIR / name).is_file()

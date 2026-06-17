"""Case Study CS1 — all six Evidence-to-Action principles must validate."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform_core.principles.validator import validate_fixture_path, validate_principles
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
CS1_DIR = REPO / "case_studies" / "cs1_wininet_proxy_drift"


def test_cs1_fixture_all_principles_compliant() -> None:
    result = validate_fixture_path(CS1_DIR / "fixture.json")
    assert result.compliant
    assert len(result.checks) == 6
    assert all(c.passed for c in result.checks)


def test_cs1_matches_expected_compliance_file() -> None:
    expected = json.loads((CS1_DIR / "expected_principle_compliance.json").read_text(encoding="utf-8"))
    result = validate_fixture_path(CS1_DIR / "fixture.json")
    assert result.compliant == expected["compliant"]
    passed_ids = {c.principle_id for c in result.checks if c.passed}
    assert passed_ids == set(expected["checks_passed"])


def test_principles_validate_cli_exit_zero() -> None:
    with patch("sys.stdout", new_callable=StringIO):
        rc = cli.main(
            ["principles", "validate", "--fixture", str(CS1_DIR / "fixture.json")],
            prog="test",
        )
    assert rc == 0


def test_diagnose_principles_cli_includes_compliance() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "diagnose",
                "--proof",
                "--principles",
                "--fixture",
                str(CS1_DIR / "fixture.json"),
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert "principle_compliance" in payload
    assert payload["principle_compliance"]["compliant"] is True


def test_proxy_report_include_principles_sections() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "proxy-report",
                "--include-principles",
                "--fixture",
                str(CS1_DIR / "fixture.json"),
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    for key in (
        "evidence_chain",
        "blocked_overclaims",
        "principle_compliance",
        "limitations",
        "safe_remediation_controls",
    ):
        assert key in payload
    assert "not probability" in payload.get("confidence_display", "")


@pytest.mark.parametrize("bad_phrase", ["proves malware", "confirmed mitm", "proven malware"])
def test_report_blocked_overclaims_detect_malware_language(bad_phrase: str) -> None:
    data = json.loads((CS1_DIR / "fixture.json").read_text(encoding="utf-8"))
    data["executive_summary"] = bad_phrase
    result = validate_principles(data)
    assert not result.compliant

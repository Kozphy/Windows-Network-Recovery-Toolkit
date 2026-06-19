"""Non-claim regression — forbidden security-product language must not appear."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from windows_network_toolkit.cli import main
from windows_network_toolkit.fleet_simulate import run_fleet_simulate
from windows_network_toolkit.reviewer_demo import run_reviewer_demo

ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN = (
    "MALWARE_DETECTED",
    "MITM_CONFIRMED",
    "COMPROMISED",
    "autonomous repair",
)

_ALLOWED_BOUNDARY = (
    "management information",
    "preview-only",
    "limitations",
    "does not prove",
)


@pytest.mark.parametrize("mode", ["big4", "faang", "mixed"])
def test_reviewer_demo_stdout_no_forbidden_phrases(mode: str) -> None:
    buf = io.StringIO()
    run_reviewer_demo(mode=mode, stream=buf)
    text = buf.getvalue().upper()
    for phrase in _FORBIDDEN:
        assert phrase.upper() not in text


def test_fleet_simulate_output_no_forbidden_phrases(tmp_path: Path) -> None:
    run_fleet_simulate(endpoints=25, seed=3, out_dir=tmp_path)
    text = (tmp_path / "incidents.jsonl").read_text(encoding="utf-8").upper()
    for phrase in _FORBIDDEN:
        assert phrase.upper() not in text


def test_fleet_simulate_all_classifications_have_limitations(tmp_path: Path) -> None:
    run_fleet_simulate(endpoints=15, seed=11, out_dir=tmp_path)
    for line in (tmp_path / "incidents.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        cls = (row.get("classification") or {}).get("primary_classification")
        if cls:
            assert "MALWARE" not in cls
            assert "MITM_CONFIRMED" not in cls
            assert row.get("limitations")


def _read_report_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return ""


def test_sample_governance_report_boundary_wording() -> None:
    path = ROOT / "reports" / "sample_governance_report.md"
    assert path.is_file()
    text = _read_report_text(path).lower()
    assert any(w in text for w in _ALLOWED_BOUNDARY)


def test_reviewer_demo_cli_main_clean() -> None:
    buf = io.StringIO()
    import sys

    old = sys.stdout
    sys.stdout = buf
    try:
        code = main(["reviewer-demo", "--mode", "mixed"])
    finally:
        sys.stdout = old
    assert code == 0
    upper = buf.getvalue().upper()
    for phrase in _FORBIDDEN:
        assert phrase.upper() not in upper

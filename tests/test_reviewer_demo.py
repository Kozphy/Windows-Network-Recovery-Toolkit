"""Tests for reviewer-demo CLI command."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from windows_network_toolkit.cli import main
from windows_network_toolkit.reviewer_demo import run_reviewer_demo

_FORBIDDEN = ("MALWARE_DETECTED", "MITM_CONFIRMED", "COMPROMISED", "autonomous repair")

_MODE_KEYWORDS = {
    "big4": ("management information", "preview-only", "control test"),
    "faang": ("reliability", "preview-only", "limitations"),
    "mixed": ("management information", "preview-only", "classification is not accusation"),
}


@pytest.mark.parametrize("mode", ["big4", "faang", "mixed"])
def test_reviewer_demo_exit_zero_each_mode(mode: str) -> None:
    assert main(["reviewer-demo", "--mode", mode]) == 0


@pytest.mark.parametrize("mode", ["big4", "faang", "mixed"])
def test_reviewer_demo_mode_keywords(mode: str) -> None:
    buf = io.StringIO()
    run_reviewer_demo(mode=mode, stream=buf)
    text = buf.getvalue().lower()
    for kw in _MODE_KEYWORDS[mode]:
        assert kw.lower() in text


@pytest.mark.parametrize("mode", ["big4", "faang", "mixed"])
def test_reviewer_demo_boundary_language(mode: str) -> None:
    buf = io.StringIO()
    run_reviewer_demo(mode=mode, stream=buf)
    text = buf.getvalue().lower()
    assert "preview-only" in text or "preview only" in text
    assert "management information" in text


@pytest.mark.parametrize("mode", ["big4", "faang", "mixed"])
def test_reviewer_demo_forbidden_absent(mode: str) -> None:
    buf = io.StringIO()
    run_reviewer_demo(mode=mode, stream=buf)
    text = buf.getvalue().upper()
    for phrase in _FORBIDDEN:
        assert phrase.upper() not in text


def test_reviewer_demo_writes_audit_when_out_set(tmp_path: Path) -> None:
    run_reviewer_demo(mode="mixed", out_dir=tmp_path, stream=io.StringIO())
    audit_file = tmp_path / "audit" / "reviewer_demo_audit.jsonl"
    assert audit_file.is_file()

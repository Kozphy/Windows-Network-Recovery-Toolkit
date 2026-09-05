"""Smoke tests for interaction report generation."""

import json
from pathlib import Path
from tempfile import mkdtemp

from research.interactions.report import run_and_report


def test_run_and_report_writes_artifacts() -> None:
    base = Path(mkdtemp(prefix="ix_report_"))
    out = run_and_report(output_dir=base, replicates=2, seed=42)
    assert out == base
    assert (base / "interaction_effects.csv").is_file()
    assert (base / "interaction_cases.jsonl").is_file()
    summary = json.loads((base / "interaction_summary.json").read_text(encoding="utf-8"))
    assert summary["manifest"]["case_count"] == 48  # 6 exp * 4 cells * 2 rep
    assert len(summary["experiments"]) == 6


def test_interaction_effects_csv_has_rows() -> None:
    base = Path(mkdtemp(prefix="ix_csv_"))
    run_and_report(output_dir=base, replicates=1, seed=7)
    lines = (base / "interaction_effects.csv").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 5  # header + 5 experiments * 4 outcomes

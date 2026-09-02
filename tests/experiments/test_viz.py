"""Tests for research visualization export."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import mkdtemp

import pytest

from experiments.viz import (
    export_powerbi_tables,
    generate_all_viz,
    generate_html_dashboard,
    load_artifacts,
    validate_artifacts,
)


def test_load_artifacts_from_repo() -> None:
    artifacts = load_artifacts()
    errors = validate_artifacts(artifacts)
    assert errors == [], errors
    assert len(artifacts.metrics) >= 4


def test_export_powerbi_tables() -> None:
    artifacts = load_artifacts()
    errors = validate_artifacts(artifacts)
    if errors:
        pytest.skip("; ".join(errors))
    out = Path(mkdtemp(prefix="viz_pbi_"))
    export_powerbi_tables(artifacts, out)
    assert (out / "dim_baseline.csv").is_file()
    assert (out / "fact_benchmark_metrics.csv").is_file()
    assert (out / "fact_bootstrap_ci.csv").is_file()
    assert (out / "manifest.json").is_file()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "dim_baseline.csv" in manifest["tables"]


def test_generate_html_dashboard() -> None:
    artifacts = load_artifacts()
    errors = validate_artifacts(artifacts)
    if errors:
        pytest.skip("; ".join(errors))
    out = Path(mkdtemp(prefix="viz_html_"))
    html_path = generate_html_dashboard(artifacts, out / "dash.html")
    content = html_path.read_text(encoding="utf-8")
    assert "Research Benchmark Dashboard" in content
    assert "chartF1" in content
    assert "B3" in content


def test_generate_all_viz() -> None:
    artifacts = load_artifacts()
    if validate_artifacts(artifacts):
        pytest.skip("benchmark artifacts not present")
    base = Path(mkdtemp(prefix="viz_all_"))
    out = generate_all_viz(html_out=base / "d.html", powerbi_out=base / "pbi")
    assert Path(out["html_dashboard"]).is_file()
    assert (Path(out["powerbi_export"]) / "fact_ablations.csv").is_file()

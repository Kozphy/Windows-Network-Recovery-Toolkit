"""Tests for classifier evaluation benchmark."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.evaluation.classifier_benchmark import (
    load_benchmark_cases,
    render_classifier_benchmark_markdown,
    run_classifier_benchmark,
)
from windows_network_toolkit.cli import main

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "examples" / "evaluation" / "classifier_benchmark_sample.json"


def test_classifier_benchmark_runs_offline() -> None:
    cases = load_benchmark_cases(SAMPLE, repo_root=ROOT)
    summary = run_classifier_benchmark(cases, repo_root=ROOT)
    assert summary.total_cases >= 8
    assert summary.unsafe_recommendation_rate == 0.0
    assert summary.exact_primary_classification_match_rate >= 0.85


def test_classifier_benchmark_markdown_report() -> None:
    cases = load_benchmark_cases(SAMPLE, repo_root=ROOT)
    summary = run_classifier_benchmark(cases, repo_root=ROOT)
    md = render_classifier_benchmark_markdown(summary)
    assert "Classifier Evaluation Report" in md
    assert "management information" in md.lower() or "malware" in md.lower()


def test_classifier_benchmark_cli_smoke() -> None:
    assert (
        main(
            [
                "classifier-benchmark",
                "--cases",
                str(SAMPLE),
                "--format",
                "json",
            ]
        )
        == 0
    )

"""Tests for evidence replay benchmark."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.evaluation.replay_benchmark import (
    load_replay_cases,
    render_replay_benchmark_markdown,
    run_replay_benchmark,
)
from windows_network_toolkit.cli import main

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "tests" / "fixtures" / "evaluation" / "replay_cases.jsonl"


def test_replay_benchmark_deterministic() -> None:
    cases = load_replay_cases(CASES, repo_root=ROOT)
    summary = run_replay_benchmark(cases, repo_root=ROOT)
    assert summary.deterministic_match_rate == 1.0
    assert summary.nondeterministic_case_count == 0


def test_replay_benchmark_markdown() -> None:
    cases = load_replay_cases(CASES, repo_root=ROOT)
    summary = run_replay_benchmark(cases, repo_root=ROOT)
    md = render_replay_benchmark_markdown(summary)
    assert "Evidence Replay Benchmark" in md
    assert "deterministic" in md.lower()


def test_replay_benchmark_cli_smoke() -> None:
    assert (
        main(
            [
                "replay-benchmark",
                "--cases",
                str(CASES),
                "--format",
                "json",
            ]
        )
        == 0
    )

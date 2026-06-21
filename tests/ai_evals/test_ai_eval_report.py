"""Tests for AI eval markdown report."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.ai_evals import load_eval_cases, render_eval_markdown, run_eval_suite

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "ai_evals" / "support_bot_cases.json"


def test_markdown_report_sections() -> None:
    report = run_eval_suite(load_eval_cases(FIXTURE))
    md = render_eval_markdown(report)
    assert "# AI Evals Feedback Loop Report" in md
    assert "## Executive summary" in md
    assert "## Eval dataset overview" in md
    assert "## Metrics summary" in md
    assert "## Failure taxonomy distribution" in md
    assert "## Policy decisions" in md
    assert "## High-risk cases requiring human review" in md
    assert "## Limitations" in md
    assert "## Recommended next actions" in md
    assert "not a formal model safety certification" in md.lower()


def test_report_includes_policy_and_limitations_per_case() -> None:
    report = run_eval_suite(load_eval_cases(FIXTURE))
    md = render_eval_markdown(report)
    assert "AE-001" in md
    assert "Recommendation is not execution authority" in md or "execution authority" in md.lower()
    assert report.total_cases == 8
    assert report.pass_count >= 1

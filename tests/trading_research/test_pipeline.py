"""MVP end-to-end pipeline."""

from __future__ import annotations

from trading_research.pipeline import run_research_pipeline


def test_run_research_pipeline(sample_csv_path, tmp_path) -> None:
    out = tmp_path / "report.md"
    result = run_research_pipeline(
        symbol="SPY",
        data_path=sample_csv_path,
        strategy_name="breakout_v1",
        output_path=out,
    )
    assert out.is_file()
    assert "Trading Research Report (MVP)" in result.report_markdown
    assert set(result.metrics.keys()) == {
        "total_return",
        "sharpe_ratio",
        "max_drawdown",
        "number_of_trades",
    }
    assert result.policy_decision in {"NEEDS_MORE_DATA", "BLOCK", "APPROVE_RESEARCH_ONLY"}

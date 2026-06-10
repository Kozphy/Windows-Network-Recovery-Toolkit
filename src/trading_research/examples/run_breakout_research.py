"""Run MVP breakout+volume confluence research on bundled sample data."""

from __future__ import annotations

from pathlib import Path

from trading_research.pipeline import run_research_pipeline

ROOT = Path(__file__).resolve().parent


def main() -> None:
    result = run_research_pipeline(
        symbol="SPY",
        data_path=ROOT / "sample_ohlcv.csv",
        strategy_name="breakout_v1",
        output_path=ROOT / "breakout_report.md",
    )
    print(result.policy_decision, result.metrics)


if __name__ == "__main__":
    main()

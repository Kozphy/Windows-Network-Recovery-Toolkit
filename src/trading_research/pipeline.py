"""MVP research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_research.backtest.engine import BacktestConfig, run_backtest
from trading_research.data.market_data import load_ohlcv_csv
from trading_research.events.detector import DetectorConfig, detect_events
from trading_research.policy.gate import apply_policy
from trading_research.reports.research_report import generate_research_report
from trading_research.signals.generator import generate_signals


@dataclass
class ResearchRunResult:
    report_markdown: str
    metrics: dict[str, Any]
    policy_decision: str
    event_count: int
    signal_count: int


def run_research_pipeline(
    *,
    symbol: str,
    data_path: str | Path,
    strategy_name: str,
    output_path: str | Path,
    detector_config: DetectorConfig | None = None,
    backtest_config: BacktestConfig | None = None,
) -> ResearchRunResult:
    """Load → detect → signal → backtest → policy → markdown report."""
    df, meta = load_ohlcv_csv(data_path, symbol=symbol)
    events = detect_events(df, symbol=symbol, config=detector_config)
    signals = generate_signals(events)
    backtest = run_backtest(df, signals, config=backtest_config or BacktestConfig())
    policy = apply_policy(backtest.metrics)

    report = generate_research_report(
        strategy_name=strategy_name,
        symbol=symbol,
        data_meta=meta.model_dump(),
        metrics=backtest.metrics,
        policy=policy,
        event_count=len(events),
        signal_count=len(signals),
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")

    return ResearchRunResult(
        report_markdown=report,
        metrics=backtest.metrics,
        policy_decision=policy.decision.value,
        event_count=len(events),
        signal_count=len(signals),
    )

"""MVP CLI for trading research."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trading_research.pipeline import run_research_pipeline


def _default_sample_csv() -> Path:
    return Path(__file__).resolve().parent / "examples" / "sample_ohlcv.csv"


def cmd_run_research(args: argparse.Namespace) -> int:
    data_path = Path(args.data)
    if not data_path.is_file():
        print(f"Data file not found: {data_path}", file=sys.stderr)
        return 1

    result = run_research_pipeline(
        symbol=args.symbol,
        data_path=data_path,
        strategy_name=args.strategy,
        output_path=args.output,
    )
    print(f"Research complete: {args.strategy} / {args.symbol}")
    print(f"  Events: {result.event_count}  Signals: {result.signal_count}")
    print(f"  Trades: {result.metrics.get('number_of_trades')}")
    print(f"  Policy: {result.policy_decision}")
    print(f"  Report: {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trading_research",
        description="Event-driven trading research MVP (not a trading bot).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-research", help="Run MVP research pipeline")
    run.add_argument("--symbol", required=True)
    run.add_argument("--data", default=str(_default_sample_csv()))
    run.add_argument("--strategy", required=True)
    run.add_argument("--output", required=True)
    run.set_defaults(func=cmd_run_research)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

"""One-command full research reproduction."""

from __future__ import annotations

import argparse
import json

from experiments.dataset import validate_dataset, write_manifest
from experiments.report import generate_technical_report
from experiments.runner import run_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce full research pipeline")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    errors = validate_dataset()
    if errors:
        print(json.dumps({"status": "error", "errors": errors}, indent=2))
        return 1

    write_manifest()
    out = run_benchmark(smoke=args.smoke, seed=args.seed)
    report_path = generate_technical_report(results_dir=out)
    print(json.dumps({"status": "ok", "results": str(out), "report": str(report_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

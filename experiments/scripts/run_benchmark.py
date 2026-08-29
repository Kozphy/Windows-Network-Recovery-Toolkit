"""Execute B0-B3 against the frozen synthetic research dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baselines import get_predictor  # noqa: E402
from experiments.baselines.common import load_dataset, verify_dataset_manifest  # noqa: E402
from experiments.scripts._shared import (  # noqa: E402
    build_run_manifest,
    git_metadata,
    load_config,
    prediction_record,
    resolve_from_root,
    run_prediction,
    write_json,
    write_jsonl,
)


def run_benchmark(config_path: Path, *, out_dir: Path | None = None) -> dict[str, Any]:
    """Run configured baselines and write raw predictions plus a run manifest."""
    config_path = config_path.resolve()
    config = load_config(config_path, expected_schema="research_benchmark_config.v1")
    dataset_root = resolve_from_root(config["dataset_root"], root=ROOT)
    manifest_path = resolve_from_root(config["dataset_manifest"], root=ROOT)
    cases, paths = load_dataset(dataset_root, splits=config["splits"])
    dataset_manifest = verify_dataset_manifest(
        manifest_path,
        dataset_root=dataset_root,
        paths=paths,
    )
    git = git_metadata(ROOT)
    rows: list[dict[str, Any]] = []
    for case in cases:
        for baseline in config["baselines"]:
            prediction, runtime_ms, replay_mismatch = run_prediction(
                get_predictor(baseline),
                case,
                repetitions=config["repetitions"],
            )
            rows.append(
                prediction_record(
                    prediction=prediction,
                    case=case,
                    benchmark_version=config["benchmark_version"],
                    dataset_version=dataset_manifest["version"],
                    dataset_digest=dataset_manifest["sha256"],
                    git_commit=git["git_commit"],
                    runtime_ms=runtime_ms,
                    replay_mismatch=replay_mismatch,
                )
            )

    destination = (out_dir or (ROOT / "experiments" / "results")).resolve()
    predictions_path = destination / config["outputs"]["predictions"]
    manifest_output = destination / config["outputs"]["run_manifest"]
    write_jsonl(predictions_path, rows)
    run_manifest = build_run_manifest(
        kind="benchmark",
        config=config,
        config_path=config_path,
        dataset_manifest=dataset_manifest,
        rows=rows,
        root=ROOT,
    )
    write_json(manifest_output, run_manifest)
    return {
        "predictions": predictions_path,
        "run_manifest": manifest_output,
        "prediction_count": len(rows),
        "replay_mismatch_count": run_manifest["replay_mismatch_count"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "experiments" / "configs" / "benchmark-v1.json",
    )
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_benchmark(args.config, out_dir=args.out_dir)
    print(f"wrote {result['prediction_count']} predictions to {result['predictions']}")
    print(f"replay mismatches: {result['replay_mismatch_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

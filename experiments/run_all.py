"""One-command full research reproduction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.dataset import validate_dataset, write_manifest
from experiments.research_docs import generate_all_research_docs
from experiments.runner import run_benchmark
from experiments.scenarios_export import sync_datasets_v1
from experiments.viz import generate_all_viz

try:
    from research.interactions.report import run_and_report as run_interactions
except ImportError:
    run_interactions = None  # type: ignore[misc, assignment]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce full research pipeline")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Experiment manifest (default experiments/manifests/v1.json)",
    )
    parser.add_argument("--skip-interactions", action="store_true")
    args = parser.parse_args(argv)

    manifest = args.manifest
    if args.smoke and manifest is None:
        manifest = Path("experiments/configs/v1.json")

    errors = validate_dataset()
    if errors:
        print(json.dumps({"status": "error", "errors": errors}, indent=2))
        return 1

    write_manifest()
    sync_datasets_v1()
    out = run_benchmark(smoke=args.smoke, seed=args.seed, manifest_path=manifest)
    docs = generate_all_research_docs(results_dir=out)

    interaction_out = None
    if not args.skip_interactions and run_interactions is not None:
        interaction_out = str(run_interactions(replicates=2 if args.smoke else 3, seed=args.seed))

    viz_out = generate_all_viz(results_dir=out)

    print(
        json.dumps(
            {
                "status": "ok",
                "results": str(out),
                "docs": docs,
                "viz": viz_out,
                "interactions": interaction_out,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

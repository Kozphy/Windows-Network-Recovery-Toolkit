"""Shared deterministic runner and artifact helpers."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.baselines.common import Prediction, proof_tier_meets_minimum, stable_digest

Predictor = Callable[[dict[str, Any]], Prediction]


def repository_root() -> Path:
    """Return the repository root from this script package."""
    return Path(__file__).resolve().parents[2]


def resolve_from_root(value: str | Path, *, root: Path | None = None) -> Path:
    """Resolve a configured path against the repository root."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (root or repository_root()) / path


def load_config(path: Path, *, expected_schema: str) -> dict[str, Any]:
    """Load and schema-check a JSON experiment config."""
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != expected_schema:
        raise ValueError(
            f"unsupported config schema {config.get('schema_version')!r}; expected {expected_schema}"
        )
    repetitions = config.get("repetitions")
    if not isinstance(repetitions, int) or repetitions < 2:
        raise ValueError("repetitions must be an integer >= 2 for replay checks")
    return config


def git_metadata(root: Path) -> dict[str, Any]:
    """Read source revision metadata without mutating the repository."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": "unknown", "tracked_worktree_dirty": None}
    return {"git_commit": commit, "tracked_worktree_dirty": bool(status)}


def runtime_environment() -> dict[str, str]:
    """Return the small environment fingerprint required for reproducibility."""
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }


def generated_at_utc() -> str:
    """Return an explicit UTC generation timestamp."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_prediction(
    predictor: Predictor,
    case: dict[str, Any],
    *,
    repetitions: int,
) -> tuple[Prediction, float, bool]:
    """Measure one prediction and replay it to detect deterministic mismatches."""
    outputs: list[Prediction] = []
    started = time.perf_counter_ns()
    outputs.append(predictor(case))
    runtime_ms = round((time.perf_counter_ns() - started) / 1_000_000, 6)
    for _ in range(repetitions - 1):
        outputs.append(predictor(case))
    stable = [output.to_dict() for output in outputs]
    replay_mismatch = any(item != stable[0] for item in stable[1:])
    return outputs[0], runtime_ms, replay_mismatch


def prediction_record(
    *,
    prediction: Prediction,
    case: dict[str, Any],
    benchmark_version: str,
    dataset_version: str,
    dataset_digest: str,
    git_commit: str,
    runtime_ms: float,
    replay_mismatch: bool,
) -> dict[str, Any]:
    """Create one raw machine-readable benchmark row."""
    expected = case["expected"]
    record = {
        "schema_version": "research_prediction.v1",
        "benchmark_version": benchmark_version,
        "dataset_version": dataset_version,
        "dataset_digest": dataset_digest,
        "git_commit": git_commit,
        "split": case["split"],
        "case_id": case["case_id"],
        "model_or_baseline": prediction.model_or_baseline,
        "expected_class": expected["classification"],
        "predicted_class": prediction.predicted_class,
        "correct": prediction.predicted_class == expected["classification"],
        "classification_supported": prediction.classification_supported,
        "proof_tier": prediction.proof_tier,
        "minimum_proof_tier": expected["minimum_proof_tier"],
        "proof_tier_meets_minimum": proof_tier_meets_minimum(
            prediction.proof_tier, expected["minimum_proof_tier"]
        ),
        "limitations": list(prediction.limitations),
        "has_explicit_limitations": bool(prediction.limitations),
        "policy_decision": prediction.policy_decision,
        "expected_policy_decision": expected["policy_decision"],
        "policy_match": prediction.policy_decision == expected["policy_decision"],
        "supporting_signals": list(prediction.supporting_signals),
        "unsafe_action_proposed": prediction.unsafe_action_proposed,
        "runtime_ms": runtime_ms,
        "replay_mismatch": replay_mismatch,
    }
    refresh_record_digest(record)
    return record


def refresh_record_digest(record: dict[str, Any]) -> None:
    """Set the digest after all stable row fields, including ablation identity, exist."""
    excluded = {"runtime_ms", "deterministic_digest"}
    digest_fields = {key: value for key, value in record.items() if key not in excluded}
    record["deterministic_digest"] = stable_digest(digest_fields)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write sorted-key JSONL with a final newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)
    path.write_text(content + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write indented, sorted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_run_manifest(
    *,
    kind: str,
    config: dict[str, Any],
    config_path: Path,
    dataset_manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    root: Path,
) -> dict[str, Any]:
    """Build a traceable manifest from the execution that produced raw rows."""
    git = git_metadata(root)
    deterministic_failures = sum(1 for row in rows if row["replay_mismatch"])
    return {
        "schema_version": "research_run_manifest.v1",
        "run_kind": kind,
        "run_id": stable_digest(
            {
                "kind": kind,
                "config": config,
                "dataset_sha256": dataset_manifest["sha256"],
                "git_commit": git["git_commit"],
            }
        )[:20],
        "generated_at_utc": generated_at_utc(),
        "benchmark_version": config["benchmark_version"],
        "config_path": config_path.relative_to(root).as_posix(),
        "config_sha256": stable_digest(config),
        "dataset": {
            "name": dataset_manifest["name"],
            "version": dataset_manifest["version"],
            "sha256": dataset_manifest["sha256"],
            "case_count": dataset_manifest["case_count"],
        },
        "prediction_count": len(rows),
        "repetitions": config["repetitions"],
        "seed": config["seed"],
        "replay_mismatch_count": deterministic_failures,
        **git,
        "environment": runtime_environment(),
        "limitations": [
            "All cases are synthetic fixtures; results do not estimate production performance.",
            "Runtime measurements are descriptive for this run and are not deterministic digests.",
            "No benchmark adapter executes remediation or changes host network state.",
        ],
    }


def ensure_script_import_path() -> None:
    """Keep direct `python experiments/scripts/...` execution importable."""
    root = str(repository_root())
    if root not in sys.path:
        sys.path.insert(0, root)

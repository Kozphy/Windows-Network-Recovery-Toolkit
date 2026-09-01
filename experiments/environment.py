"""Runtime environment metadata for reproducibility."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.dataset import DEFAULT_DATASET_DIR, build_manifest, repo_root


def git_sha(root: Path | None = None) -> str:
    base = root or repo_root()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=base,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    for pkg in ("pydantic", "pytest"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not_installed"
    return versions


def build_run_metadata(
    *,
    run_id: str,
    dataset_dir: Path | None = None,
    random_seed: int = 42,
    smoke: bool = False,
) -> dict[str, Any]:
    """Collect reproducibility metadata for a benchmark run."""
    root = repo_root()
    manifest = build_manifest(dataset_dir or DEFAULT_DATASET_DIR)
    return {
        "run_id": run_id,
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        "git_sha": git_sha(root),
        "python_version": sys.version,
        "platform": platform.platform(),
        "dependency_versions": dependency_versions(),
        "dataset_version": manifest.dataset_version,
        "dataset_hashes": manifest.files,
        "case_count": manifest.case_count,
        "random_seed": random_seed,
        "smoke_mode": smoke,
        "repo_root": str(root),
    }


def stable_digest(payload: Any) -> str:
    """Deterministic SHA-256 over JSON-serialized payload."""
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

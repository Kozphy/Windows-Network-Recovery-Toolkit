"""Append-only persistence and replay for edge reasoning runs.

Module responsibility:
    Append each :class:`~edge_device.models.EdgeReasoningRun` to ``logs/edge_runs.jsonl``
    (one JSON object per line) and reload a run by ``run_id`` for deterministic replay
    without re-probing or re-simulating.

System placement:
    Called by :mod:`edge_device.cli_handlers`. Mirrors the append-only JSONL contract used
    across the toolkit (``platform_core.event_store``, ``order_flow_simulator``).

Key invariants:
    * Append-only; rows are never mutated or deleted.
    * Replay returns the stored decision verbatim — it does not recompute or re-probe.

Side effects:
    Creates ``logs/`` and appends UTF-8 JSON lines.

Audit Notes:
    To dispute an edge decision, locate the row by ``run_id`` in ``logs/edge_runs.jsonl``;
    it contains the full observation/event/transition/policy chain captured at decision time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from edge_device.models import EdgeReasoningRun

EDGE_RUNS_REL = "logs/edge_runs.jsonl"


def edge_runs_path(repo_root: Path) -> Path:
    """Return the append-only edge runs JSONL path under ``repo_root``."""
    return repo_root / EDGE_RUNS_REL


def append_edge_run(repo_root: Path, run: EdgeReasoningRun) -> Path:
    """Append one edge run's output contract to ``logs/edge_runs.jsonl``.

    Args:
        repo_root: Toolkit checkout root.
        run: Completed reasoning run.

    Returns:
        Path written.

    Side effects:
        Creates ``logs/`` if needed and appends one JSON line.
    """
    path = edge_runs_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(run.to_output_dict(), ensure_ascii=False, default=str) + "\n")
    return path


def load_edge_run(repo_root: Path, run_id: str) -> dict[str, Any] | None:
    """Return the last stored run dict matching ``run_id`` (read-only, no recompute).

    Args:
        repo_root: Toolkit checkout root.
        run_id: Edge run identifier from a prior ``edge-diagnose``.

    Returns:
        Stored output dict, or ``None`` when not found. Malformed lines are skipped.
    """
    path = edge_runs_path(repo_root)
    if not path.is_file():
        return None
    rid = run_id.strip()
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and str(row.get("run_id")) == rid:
            last = row
    return last

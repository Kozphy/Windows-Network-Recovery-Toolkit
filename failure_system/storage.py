"""Append-only JSONL persistence for ``FailureBlock`` records (daily shards).

System placement:
    Written by ``failure_system.cli.cmd_diagnose`` and FastAPI ``POST /diagnose``; read by search,
    recommend, and listing endpoints.

Key invariants:
    - Each JSON object occupies exactly one line (newline delimited, UTF-8).
    - Shard filenames follow ``YYYY-MM-DD.jsonl`` in UTC calendar days derived from
      ``FailureBlock.created_at.date()``.

Side effects:
    ``append_failure_block`` creates directories and appends bytes without file locking.

Idempotency:
    Re-invoking append generates duplicate lines when diagnoses rerun—dedupe using ``FailureBlock.id``
    client-side if needed.

Audit Notes:
    Tampering with shards breaks ``FailureBlock.model_validate`` consumers—keep backups before manual edits.

Failure modes:
    Concurrent writers may interleave partial lines; readers should skip malformed JSON gracefully.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterator
from uuid import UUID

from failure_system.models import FailureBlock

DEFAULT_RELATIVE = Path("data") / "failure_blocks"


def default_data_dir(root: Path | None = None) -> Path:
    """Resolve ``<repo>/data/failure_blocks`` relative to this package.

    Args:
        root: Optional repository root; defaults to parent of the ``failure_system`` package directory.

    Returns:
        Absolute path to the JSONL directory (may not exist yet).
    """
    if root is not None:
        return root / DEFAULT_RELATIVE
    here = Path(__file__).resolve().parent.parent
    return here / DEFAULT_RELATIVE


def _shard_path(data_dir: Path, day: date | None = None) -> Path:
    d = day or date.today()
    return data_dir / f"{d.isoformat()}.jsonl"


def ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def append_failure_block(block: FailureBlock, data_dir: Path | None = None) -> Path:
    """Append ``block`` as ``model_dump(mode="json")`` to the UTC-day shard file.

    Args:
        block: Failure knowledge record including timezone-aware ``created_at``.
        data_dir: Override directory; defaults to ``default_data_dir()``.

    Returns:
        Absolute path of the shard written (created if missing).

    Raises:
        OSError: Propagates when the process lacks permission to create/write files.
    """
    target_dir = data_dir or default_data_dir()
    ensure_data_dir(target_dir)
    path = _shard_path(target_dir, block.created_at.date())
    payload = block.model_dump(mode="json")
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return path


def iter_failure_blocks(data_dir: Path | None = None) -> Iterator[FailureBlock]:
    """Yield ``FailureBlock`` rows from every ``*.jsonl`` shard sorted lexically by filename.

    Args:
        data_dir: Directory containing shards; missing directories yield no rows.

    Yields:
        Validated ``FailureBlock`` instances in shard order, line order within shards.

    Raises:
        pydantic.ValidationError: When a line contains JSON that fails schema validation.
    """
    target_dir = data_dir or default_data_dir()
    if not target_dir.is_dir():
        return
    for path in sorted(target_dir.glob("*.jsonl")):
        yield from iter_shard(path)


def iter_shard(path: Path) -> Iterator[FailureBlock]:
    """Parse ``path`` line-by-line into ``FailureBlock`` objects."""

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            yield FailureBlock.model_validate(obj)


def load_failure_block_by_id(block_id: UUID, data_dir: Path | None = None) -> FailureBlock | None:
    """Scan stored shards linearly until ``block_id`` matches or iterators exhaust.

    Args:
        block_id: Identifier previously emitted by ``generator.build_failure_block``.
        data_dir: Shard directory override.

    Returns:
        Matching ``FailureBlock`` or ``None`` when absent.

    Engineering Notes:
        Linear scan suits local KB sizes; large installs should externalize indexing if needed.
    """
    for block in iter_failure_blocks(data_dir):
        if block.id == block_id:
            return block
    return None


def list_shard_files(data_dir: Path | None = None) -> list[Path]:
    """Return sorted shard paths for maintenance scripts."""

    target_dir = data_dir or default_data_dir()
    if not target_dir.is_dir():
        return []
    return sorted(target_dir.glob("*.jsonl"))

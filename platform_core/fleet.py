"""Fleet extension placeholders (no remote control in the local prototype).

Future: signed policy bundles, mTLS agent auth, multi-tenant routing — see
``docs/fleet_architecture.md``.

This module also hosts **cross-package linkage helpers** between platform ``FailureEvent``
rows and persisted ``FailureKnowledge`` shards (failure_system JSONL) when both are enabled
locally—the backend uses these for enriched ``GET`` responses without breaking local-first bounds.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class FleetConfigStub:
    """Reserved for future fleet policy sync (content-addressed bundles)."""

    enabled: bool = False


def failure_system_blocks_dir() -> Path:
    """Resolve Failure Knowledge JSONL root (respects ``FAILURE_SYSTEM_DATA_DIR``)."""

    from failure_system.storage import default_data_dir

    raw = os.environ.get("FAILURE_SYSTEM_DATA_DIR")
    if raw:
        return Path(raw).resolve()
    return default_data_dir()


def linked_failure_block_payload(failure_block_id: str) -> dict[str, Any]:
    """Best-effort load of a FailureBlock summary for linkage to ``FailureEvent``.

    Args:
        failure_block_id: UUID string emitted by ``failure_system.generator`` (stored on events).

    Returns:
        Serialized payload with ``found`` boolean; when ``found`` is ``True``, includes a
        ``failure_block_summary`` dict safe for JSON (no subprocess, read-only filesystem scan).

    Side effects:
        Reads ``*.jsonl`` under the failure-system data dir (same as diagnose/search).

    Idempotency:
        Read-only with respect to KB contents; repeating with the same disk state returns
        identical structure.
    """
    raw = (failure_block_id or "").strip()
    if not raw:
        return {"found": False, "failure_block_id": "", "detail": "no_failure_block_id"}

    try:
        uid = UUID(raw)
    except ValueError:
        return {"found": False, "failure_block_id": raw, "detail": "invalid_failure_block_uuid"}

    try:
        from failure_system.models import failure_block_to_summary
        from failure_system.storage import load_failure_block_by_id
    except ImportError:
        return {"found": False, "failure_block_id": raw, "detail": "failure_system_unavailable"}

    block = load_failure_block_by_id(uid, failure_system_blocks_dir())
    if block is None:
        return {
            "found": False,
            "failure_block_id": raw,
            "detail": "not_in_local_failure_kb",
        }

    summary = failure_block_to_summary(block)
    return {
        "found": True,
        "failure_block_id": raw,
        "failure_block_summary": summary.model_dump(mode="json"),
    }

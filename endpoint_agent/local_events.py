"""Persist agent-local telemetry rows under ``platform_data/endpoint_agent_events.jsonl``.

Module responsibility:
    Append chronological JSON lines describing agent heartbeat phases independent of remote API success.

System placement:
    Invoked from :mod:`endpoint_agent.service_runner` (loop) and optionally future hooks; distinct from
    ``logs/`` CLI streams to keep platform analytics co-located under ``PLATFORM_DATA_DIR``.

Key invariants:
    * Always UTF-8 newline JSON (see :func:`~platform_core.storage.append_jsonl`).
    * Inserts RFC3339-ish ``timestamp`` via :func:`~platform_core.models.utc_now_iso` when caller omits field.

Side effects:
    Creates parent directories implicitly through storage helper.

Failures:
    Disk errors bubble as ``OSError`` from :func:`~platform_core.storage.append_jsonl`.

Audit Notes:
    Compare with ``platform_signals.jsonl`` / ``endpoints.jsonl`` when reconciling agent outages—timestamp skew indicates clock drift, not logic bugs.
"""

from __future__ import annotations

from typing import Any

from platform_core.models import utc_now_iso
from platform_core.storage import append_jsonl, platform_data_dir


def append_agent_event(record: dict[str, Any]) -> None:
    """Append one sanitized agent event row with default timestamp injection.

    Args:
        record: JSON-serializable mapping (``phase`` recommended for downstream analytics).

    Raises:
        ``OSError`` if ``platform_data`` destination not writable.

    Idempotency:
        Not idempotent—each call appends a distinct line (no dedupe).
    """

    enriched = dict(record)
    enriched.setdefault("timestamp", utc_now_iso())
    append_jsonl(platform_data_dir() / "endpoint_agent_events.jsonl", enriched)

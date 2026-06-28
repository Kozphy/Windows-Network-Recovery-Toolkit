"""Append-only JSONL audit sink (local disk only; no upload).

Module responsibility:
    Persist one JSON-serializable audit event per line; callers own schema and timestamps.

System placement:
    Used by ``src.cli._audit``, ``src.network_recovery.audit``, and guardian/remediation
    paths that require durable local audit trails.

Key invariants:
    * Append-only — repeated calls add rows; not idempotent.
    * No network upload or remote sink from this module.
    * Creates parent directories before first write.

Side effects:
    * Creates ``path.parent`` if missing and appends one UTF-8 JSONL line to ``path``.

Audit Notes:
    Partial writes or disk exhaustion are file-level concerns; rotate or back up JSONL
    outside this API if line-count growth or parse failures are observed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object line to local audit log file.

    Side effects:
        - Creates parent directories if missing.
        - Appends one line to `path`.

    Idempotency:
        Not idempotent; repeated calls append additional entries.

    Args:
        path: Destination JSONL file path.
        payload: JSON-serializable audit event payload.

    Raises:
        TypeError: If payload contains non-serializable values.
        OSError: If file cannot be created or written.

    Audit Notes:
        Inspect line count growth and parse failures if disk fills or partial
        writes occur; recovery is file-level backup/rotation outside this API.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")

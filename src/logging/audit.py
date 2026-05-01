"""Append-only JSONL audit sink (local only)."""

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
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")

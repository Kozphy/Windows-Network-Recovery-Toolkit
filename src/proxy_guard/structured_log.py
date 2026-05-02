"""JSON-lines structured logging for Proxy Guard (machine-parseable, consistent schema)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, TextIO

from ..core.time_utils import utc_now_iso

_SCHEMA_VERSION = "1"


def _append_file(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.write("\n")


def emit_structured_log(
    *,
    logger: str,
    level: str,
    event: str,
    stream: TextIO | None = None,
    file_path: Path | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit one JSON object (single line) for operators and log aggregators.

    Schema (stable keys):
        ``schema_version``, ``timestamp``, ``logger``, ``level``, ``event``, plus any
        ``extra`` fields.

    Each invocation writes one line to ``sys.stderr`` (or ``stream``) and, when
    ``file_path`` is set, duplicates the same line to that append-only path.
    """
    row: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "timestamp": utc_now_iso(),
        "logger": logger,
        "level": level.upper(),
        "event": event,
    }
    if extra:
        for k, v in extra.items():
            row[k] = v
    line = json.dumps(row, ensure_ascii=False, default=str)
    out = stream if stream is not None else sys.stderr
    out.write(line + "\n")
    out.flush()
    if file_path is not None:
        _append_file(file_path, line)
    return row

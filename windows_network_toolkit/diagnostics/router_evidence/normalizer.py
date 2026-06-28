"""Normalize router events to canonical JSONL.

Module responsibility:
    Write importer output as schema-tagged JSONL with router-level evidence metadata.

System placement:
    Called by ``router_evidence.runner`` after import; output feeds correlation pipelines.

Key invariants:
    * Overwrites ``out_path`` on each run — not append-only.
    * Every line includes ``schema_version`` and ``evidence_source``.
    * Limitations clarify import is normalized evidence, not packet capture.

Side effects:
    * Creates parent directories and writes/replaces the target JSONL file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ROUTER_SCHEMA


def write_router_jsonl(events: list[dict[str, Any]], out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for ev in events:
            row = {**ev, "schema_version": ROUTER_SCHEMA, "evidence_source": "ROUTER_LEVEL_EVIDENCE"}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "ok": True,
        "schema_version": ROUTER_SCHEMA,
        "event_count": len(events),
        "out_path": str(out_path),
        "limitations": [
            "Router import is read-only — normalized evidence only.",
            "Imported logs are router-level evidence — not packet-capture proof.",
        ],
    }

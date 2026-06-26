"""Normalize router events to canonical JSONL."""

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

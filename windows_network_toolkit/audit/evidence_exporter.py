"""Export evidence bundles to JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_evidence(bundle: Any, path: Path | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = bundle.model_dump() if hasattr(bundle, "model_dump") else dict(bundle)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def export_timeline(timeline: list[dict[str, Any]], path: Path | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    return p

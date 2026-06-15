"""JSON Schema export for Evidence Case models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EvidenceCase

DEFAULT_SCHEMA_PATH = Path("schemas/evidence_case.schema.json")


def export_json_schema(*, indent: int = 2) -> dict[str, Any]:
    """Return JSON Schema for the root EvidenceCase model."""
    return EvidenceCase.model_json_schema()


def write_json_schema(path: str | Path = DEFAULT_SCHEMA_PATH, *, indent: int = 2) -> Path:
    """Write JSON Schema to disk."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(export_json_schema(), indent=indent),
        encoding="utf-8",
    )
    return target

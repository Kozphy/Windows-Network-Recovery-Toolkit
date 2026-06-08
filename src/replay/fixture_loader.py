"""Load proxy incident fixtures for portable demo/CI replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "proxy_incidents"


def list_fixture_paths(directory: Path | None = None) -> list[Path]:
    root = directory or FIXTURES_DIR
    if not root.is_dir():
        return []
    return sorted(root.glob("*.json"))


def load_fixture(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    blob = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(blob, dict):
        raise ValueError(f"Fixture must be a JSON object: {p}")
    blob.setdefault("incident_id", p.stem)
    return blob


def load_all_fixtures(directory: Path | None = None) -> list[dict[str, Any]]:
    return [load_fixture(p) for p in list_fixture_paths(directory)]

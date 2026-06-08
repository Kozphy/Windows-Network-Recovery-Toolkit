from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_core.decision_domain import Decision, parse_decision


@pytest.fixture
def fixture_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "fixtures" / "decision_domain" / "proxy_preview_decision.json"
    assert path.is_file(), f"missing {path}"
    return path


@pytest.fixture
def sample_decision(fixture_path: Path) -> Decision:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    return parse_decision(raw)

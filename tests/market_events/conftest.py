from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def calendar_fixture() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "fixtures" / "market_events" / "calendar.json"
    assert path.is_file(), f"missing {path}"
    return path


@pytest.fixture
def reviews_fixture() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "fixtures" / "market_events" / "reviews.json"
    assert path.is_file(), f"missing {path}"
    return path

from __future__ import annotations

from pathlib import Path

import pytest

from src.market_events.calendar import get_event, load_calendar


def test_load_calendar_fixture(calendar_fixture: Path) -> None:
    events = load_calendar(calendar_fixture)
    assert len(events) >= 4
    assert events[0].event_id


def test_get_event_by_id(calendar_fixture: Path) -> None:
    event = get_event("CPI_2026_06", calendar_fixture)
    assert event.category.value == "MACRO"
    assert "BTC" in event.affected_assets


def test_unknown_event_raises(calendar_fixture: Path) -> None:
    with pytest.raises(KeyError):
        get_event("NO_SUCH_EVENT", calendar_fixture)

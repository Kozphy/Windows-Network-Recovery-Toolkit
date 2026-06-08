from __future__ import annotations

from pathlib import Path

from src.market_events.models import ThesisOutcome, VolatilityExpectation
from src.market_events.review import get_review, load_reviews


def test_load_reviews(reviews_fixture: Path) -> None:
    reviews = load_reviews(reviews_fixture)
    assert len(reviews) >= 1
    assert reviews[0].event_id


def test_get_review_cpi(reviews_fixture: Path) -> None:
    review = get_review("CPI_2026_06", reviews_fixture)
    assert review.expected_volatility == VolatilityExpectation.HIGH
    assert review.thesis_correct == ThesisOutcome.TRUE
    assert review.lessons_learned

"""Deterministic replay of calendar scoring across fixtures."""

from __future__ import annotations

from pathlib import Path

from .audit import canonical_json_hash
from .calendar import load_calendar
from .review import load_reviews
from .scoring import score_event


def replay_all(calendar_path: Path | None = None, reviews_path: Path | None = None) -> dict[str, object]:
    events = load_calendar(calendar_path)
    reviews = load_reviews(reviews_path)
    scores = [score_event(ev).model_dump(mode="json") for ev in events]
    digest = canonical_json_hash(scores)
    return {
        "event_count": len(events),
        "review_count": len(reviews),
        "scores_digest": digest,
        "scores": scores,
        "reviews": [r.model_dump(mode="json") for r in reviews],
    }

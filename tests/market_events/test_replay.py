from __future__ import annotations

from pathlib import Path

from src.market_events.replay import replay_all


def test_replay_determinism(calendar_fixture: Path, reviews_fixture: Path) -> None:
    digest_a = replay_all(calendar_fixture, reviews_fixture)
    digest_b = replay_all(calendar_fixture, reviews_fixture)
    assert digest_a == digest_b
    assert digest_a["event_count"] >= 4
    assert digest_a["review_count"] >= 1
    assert len(digest_a["scores_digest"]) == 64

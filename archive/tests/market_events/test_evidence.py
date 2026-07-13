from __future__ import annotations

from pathlib import Path

from src.market_events.calendar import get_event
from src.market_events.evidence import build_evidence_tree
from src.market_events.scoring import score_event


def test_evidence_tree_structure(calendar_fixture: Path) -> None:
    event = get_event("CPI_2026_06", calendar_fixture)
    score = score_event(event)
    tree = build_evidence_tree(event, score)
    assert tree.observation
    assert tree.candidate_interpretation
    assert tree.confidence >= 0
    assert tree.final_research_note

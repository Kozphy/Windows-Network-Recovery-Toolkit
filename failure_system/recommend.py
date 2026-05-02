"""Project persisted ``FailureBlock`` rows into ``FixRecommendation`` payloads.

System placement:
    Shared by FastAPI ``POST /recommend-fix`` and ``failure_system.cli.cmd_recommend``.

Side effects:
    None—read-only scans of JSONL shards via ``search`` / ``storage``.

Constraints:
    Always sets ``requires_explicit_confirmation=True`` so downstream UIs cannot imply automation.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from failure_system.models import FailureBlock, FixRecommendation
from failure_system.search import search_failure_blocks
from failure_system.storage import load_failure_block_by_id


def recommendation_from_block(block: FailureBlock) -> FixRecommendation:
    """Convert a stored FailureBlock into narrative recommendation-only metadata.

    Args:
        block: Source failure knowledge row.

    Returns:
        ``FixRecommendation`` suitable for JSON serialization.
    """
    return FixRecommendation(
        failure_block_id=block.id,
        title=block.name,
        rationale=(
            f"Confidence {block.confidence_score:.2f} based on deterministic rules over observed signals: "
            + "; ".join(block.observed_signals[:6])
        ),
        recommended_fix=block.recommended_fix,
        risk_level=block.risk_level,
        rollback_plan=block.rollback_plan,
        safety_notes=block.safety_boundary,
        requires_explicit_confirmation=True,
    )


def recommend_by_id(block_id: UUID, data_dir: Path | None = None) -> FixRecommendation | None:
    """Linear-scan shards for ``block_id`` and project the match."""

    block = load_failure_block_by_id(block_id, data_dir)
    if block is None:
        return None
    return recommendation_from_block(block)


def recommend_by_query(query: str, data_dir: Path | None = None) -> FixRecommendation | None:
    """Return a recommendation for the newest FailureBlock matching ``query``."""

    hits = search_failure_blocks(query, data_dir=data_dir, limit=1)
    if not hits:
        return None
    return recommendation_from_block(hits[0])

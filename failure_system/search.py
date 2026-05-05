"""Token-AND text search for locally persisted ``FailureBlock`` JSONL.

System placement:
    Invoked from ``failure_system.cli.cmd_search``, ``GET /failure-blocks/search``, and
    ``recommend.recommend_by_query`` (first hit only).

Input assumptions:
    Query strings are split on whitespace after lowercasing; every token must appear in the
    combined searchable text (symptom, causes, command output, fix text, etc.).

Output guarantees:
    Results sort by ``created_at`` descending and honor ``limit`` as a post-filter cap.

Side effects:
    None—read-only traversal of shard files.
"""

from __future__ import annotations

import re
from pathlib import Path

from failure_system.models import FailureBlock
from failure_system.storage import iter_failure_blocks


def _norm(q: str) -> str:
    """Normalize search text to lowercase single-spaced tokens."""
    return re.sub(r"\s+", " ", q.strip().lower())


def matches_query(block: FailureBlock, query: str) -> bool:
    """Check whether all normalized query tokens occur in the block's searchable text.

    Args:
        block: Failure knowledge record to inspect.
        query: Free-text string; empty or whitespace-only matches every block.

    Returns:
        ``True`` when the AND-of-tokens predicate passes.
    """
    if not query.strip():
        return True
    haystack_parts: list[str] = [
        block.symptom,
        block.name,
        block.recommended_fix,
        " ".join(block.likely_causes),
        " ".join(block.observed_signals),
        " ".join(block.source_logs),
    ]
    for value in block.diagnostic_commands.values():
        haystack_parts.append(value)
    haystack = _norm(" ".join(haystack_parts))
    tokens = _norm(query).split()
    return all(t in haystack for t in tokens)


def search_failure_blocks(
    query: str,
    *,
    data_dir: Path | None = None,
    limit: int = 50,
) -> list[FailureBlock]:
    """Filter stored blocks with ``matches_query`` and return the newest ``limit`` rows.

    Args:
        query: Token-AND string as documented in ``matches_query``.
        data_dir: JSONL root; defaults to ``storage.default_data_dir()``.
        limit: Maximum number of blocks to return after sorting.

    Returns:
        Newest-first list bounded by ``limit`` (may be shorter than ``limit``).
    """
    matches: list[FailureBlock] = []
    for block in iter_failure_blocks(data_dir):
        if matches_query(block, query):
            matches.append(block)
    matches.sort(key=lambda b: b.created_at, reverse=True)
    return matches[:limit]

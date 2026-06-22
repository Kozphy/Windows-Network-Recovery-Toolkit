"""Bounded retry policy for queue workers."""

from __future__ import annotations

MAX_RETRIES = 3
BACKOFF_SECONDS = (1, 5, 15)


def should_retry(attempt: int) -> bool:
    return attempt < MAX_RETRIES


def backoff_seconds(attempt: int) -> int:
    if attempt < 0:
        return BACKOFF_SECONDS[0]
    return BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]

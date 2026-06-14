"""In-memory usage limits for agent requests (portfolio-safe; replace with Redis in prod)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class UsageLimiter:
    max_requests_per_window: int = 60
    window_seconds: int = 60
    _buckets: dict[str, list[float]] = field(default_factory=dict)

    def check(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        key = user_id or "anonymous"
        hits = [t for t in self._buckets.get(key, []) if now - t < self.window_seconds]
        if len(hits) >= self.max_requests_per_window:
            return False, f"rate limit exceeded for user {key}"
        hits.append(now)
        self._buckets[key] = hits
        return True, "ok"

    def reset(self) -> None:
        self._buckets.clear()


_default_limiter = UsageLimiter()


def get_usage_limiter() -> UsageLimiter:
    return _default_limiter

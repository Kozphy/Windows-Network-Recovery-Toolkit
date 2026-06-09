"""Process inventory collector facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def collect_process_signals(
    *,
    run: Callable[..., Any] | None = None,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Capture recent process inventory and proxy actor candidates."""
    from src.proxy_guard.process_inventory import (
        capture_process_inventory,
        heuristic_proxy_actor_candidates,
    )

    kwargs: dict[str, Any] = {}
    if run is not None:
        kwargs["run"] = run
    inventory = capture_process_inventory(**kwargs)
    candidates = heuristic_proxy_actor_candidates(inventory, max_rows=max_rows)
    return {
        "process_count": len(inventory),
        "candidates": [c.to_dict() if hasattr(c, "to_dict") else dict(c) for c in candidates[:max_rows]],
        "source": "win32_process_inventory",
    }

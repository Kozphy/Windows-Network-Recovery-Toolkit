"""Factories for append-only Proxy Guard JSONL records.

Schemas stay intentionally flat for ``json.loads(line)`` review in text editors.
"""

from __future__ import annotations

from typing import Any

from ..core.time_utils import utc_now_iso


def proxy_guard_event(
    *,
    event_type: str,
    registry_view: dict[str, Any],
    owners: dict[str, Any] | None = None,
    notes: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build one JSONL-safe event row."""
    return {
        "type": "proxy_guard",
        "event_type": event_type,
        "timestamp": utc_now_iso(),
        "registry": registry_view,
        "owners": owners or {},
        "notes": list(notes),
    }

"""Windows event log / Sysmon collector facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def collect_eventlog_signals(
    *,
    run: Callable[..., Any] | None = None,
    max_events: int = 25,
) -> dict[str, Any]:
    """Collect Sysmon proxy-related events when available."""
    from src.proxy_guard.sysmon_attribution import collect_sysmon_proxy_events

    kwargs: dict[str, Any] = {"max_events": max_events}
    if run is not None:
        kwargs["run"] = run
    rows = collect_sysmon_proxy_events(**kwargs)

    def _serialize_row(row: Any) -> Any:
        if isinstance(row, dict):
            return row
        to_dict = getattr(row, "to_dict", None)
        return to_dict() if callable(to_dict) else row

    serialized = [_serialize_row(row) for row in rows]
    return {
        "event_count": len(serialized),
        "events": serialized[:max_events],
        "source": "sysmon_operational",
    }

"""Storage package for dashboard evidence events (schema + append-only store)."""

from windows_network_toolkit.storage.event_store import EvidenceEventStore
from windows_network_toolkit.storage.events import (
    DEFAULT_LIMITATIONS,
    EvidenceEvent,
    new_event_id,
    utc_now_iso,
)

__all__ = [
    "DEFAULT_LIMITATIONS",
    "EvidenceEvent",
    "EvidenceEventStore",
    "new_event_id",
    "utc_now_iso",
]

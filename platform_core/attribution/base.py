"""Attribution providers — never synthesize forensic proof without authoritative sources."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from platform_core.events import ActorAttribution


@runtime_checkable
class AttributionProvider(Protocol):
    """Pluggable heuristic or evidence-backed attribution implementations."""

    name: str

    def describe(self) -> str:
        """Human-readable capability description for docs / dashboards."""

        ...

    def attribute(self, context: dict[str, Any]) -> ActorAttribution:
        """Return best-effort :class:`~platform_core.events.ActorAttribution` for ``context``."""


def unattributed() -> ActorAttribution:
    """Neutral placeholder when probes are unavailable."""

    return ActorAttribution(
        confidence="none",
        method="none",
        notes=["Attribution unavailable or not requested."],
        provider="noop",
        details={},
    )

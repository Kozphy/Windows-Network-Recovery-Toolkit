"""Optional psutil-backed snapshot (import guarded)."""

from __future__ import annotations

from typing import Any

from platform_core.attribution.polling import PollingHeuristicProvider
from platform_core.events import ActorAttribution


class PsutilSnapshotProvider:
    """Enumerates process names when ``psutil`` is importable; otherwise degrades gracefully."""

    name = "psutil_optional_v1"

    def describe(self) -> str:
        return (
            "If psutil is installed, derives a sanitized name list-only snapshot; attribution stays "
            "heuristic/low confidence."
        )

    def attribute(self, context: dict[str, Any]) -> ActorAttribution:
        limit = min(int(context.get("psutil_limit") or 200), 500)
        try:
            import psutil  # type: ignore import-not-found
        except ImportError:
            return ActorAttribution(
                confidence="none",
                method="psutil_unavailable",
                notes=["psutil not installed; skipping optional enumerator."],
                provider=self.name,
                details={},
            )

        names: list[str] = []
        try:
            for p in psutil.process_iter(attrs=["name"]):  # type: ignore[attr-defined]
                info = getattr(p, "info", None) or {}
                n = info.get("name")
                if callable(n):
                    n = n()
                if isinstance(n, str):
                    names.append(n.lower())
                if len(names) >= limit:
                    break
        except Exception as exc:  # noqa: BLE001 — best-effort platform layer
            return ActorAttribution(
                confidence="none",
                method="psutil_error",
                notes=["Enumeration failed; attribution unavailable."],
                provider=self.name,
                details={"error": exc.__class__.__name__},
            )

        polled = PollingHeuristicProvider().attribute({"process_names_sample": names})
        details = dict(polled.details)
        details.setdefault("sample_size", len(names))
        return ActorAttribution(
            confidence=polled.confidence,
            method=polled.method,
            notes=list(polled.notes),
            provider=f"{self.name}+{PollingHeuristicProvider.name}",
            details=details,
        )

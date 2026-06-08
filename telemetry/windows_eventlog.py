"""Windows Event Log registry-write parser abstraction (fixture-first, read-only)."""

from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from typing import Any

from telemetry.models import RegistryWriteEvent
from telemetry.sysmon_parser import (
    is_relevant_proxy_registry_path,
    normalize_registry_path,
    parse_sysmon_registry_event,
)

EVENTLOG_UNAVAILABLE = (
    "Windows Event Log query is unavailable on this platform or without optional dependencies."
)


class EventLogNotAvailableError(RuntimeError):
    """Raised when live Event Log access is explicitly requested but unsupported."""


def _coerce_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_eventlog_timestamp(raw: dict[str, Any], warnings: list[str]) -> datetime:
    for key in ("TimeCreated", "timestamp_utc", "timestamp", "UtcTime"):
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            warnings.append(f"unparseable_timestamp:{key}={text}")
    warnings.append("missing_timestamp_defaulted_to_epoch")
    return datetime(1970, 1, 1, tzinfo=UTC)


def parse_windows_registry_event(raw: dict[str, Any]) -> RegistryWriteEvent | None:
    """Parse Security 4657 / Sysmon-like fixture rows into :class:`RegistryWriteEvent`."""
    if raw.get("EventID") == 13 or raw.get("Id") == 13:
        event = parse_sysmon_registry_event(raw)
        if event is not None:
            return RegistryWriteEvent(
                timestamp_utc=event.timestamp_utc,
                source="windows_eventlog",
                event_id=event.event_id,
                registry_path=event.registry_path,
                registry_value_name=event.registry_value_name,
                registry_value_data=event.registry_value_data,
                process_guid=event.process_guid,
                process_id=event.process_id,
                process_name=event.process_name,
                process_path=event.process_path,
                command_line=event.command_line,
                user=event.user,
                raw_event=event.raw_event,
                parse_warnings=event.parse_warnings,
            )

    warnings: list[str] = []
    event_id = _coerce_int(raw.get("EventID") or raw.get("Id"))
    if event_id not in {4657, 13}:
        return None

    registry_path = normalize_registry_path(
        str(
            raw.get("ObjectName")
            or raw.get("TargetObject")
            or raw.get("registry_path")
            or raw.get("RegistryPath")
            or ""
        )
    )
    if not registry_path or not is_relevant_proxy_registry_path(registry_path):
        return None

    process_path = str(
        raw.get("ProcessName") or raw.get("Image") or raw.get("process_path") or ""
    ).strip()
    process_id = _coerce_int(raw.get("ProcessId") or raw.get("ProcessID"))
    if not process_path:
        warnings.append("missing_process_path")
    if process_id is None:
        warnings.append("missing_process_id")

    value_name = raw.get("ObjectValueName") or raw.get("value_name")
    if value_name is None and registry_path:
        value_name = registry_path.rsplit("\\", 1)[-1]

    return RegistryWriteEvent(
        timestamp_utc=_parse_eventlog_timestamp(raw, warnings),
        source="windows_eventlog",
        event_id=event_id,
        registry_path=registry_path,
        registry_value_name=str(value_name) if value_name else None,
        registry_value_data=str(
            raw.get("NewValue") or raw.get("Details") or raw.get("registry_value_data") or ""
        )
        or None,
        process_guid=str(raw.get("ProcessGuid") or "") or None,
        process_id=process_id,
        process_name=(process_path.rsplit("\\", 1)[-1] if process_path else None),
        process_path=process_path or None,
        command_line=str(raw.get("CommandLine") or "") or None,
        user=str(raw.get("SubjectUserName") or raw.get("User") or "") or None,
        raw_event=dict(raw),
        parse_warnings=warnings,
    )


def query_windows_eventlog_preview(
    *,
    since_seconds: int = 120,
    max_events: int = 200,
    run: Any = subprocess.run,
) -> list[RegistryWriteEvent]:
    """Best-effort live preview; returns [] on non-Windows without mutating system state."""
    _ = since_seconds, max_events, run
    if platform.system().lower() != "windows":
        return []
    # Live wevtutil/XML parsing is optional; fixture parsing covers tests and imports.
    return []

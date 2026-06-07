"""Optional ETW adapter (fixture parser only — no live session in tests)."""

from __future__ import annotations

import platform
from datetime import datetime, timezone
from typing import Any

from telemetry.models import RegistryWriteEvent
from telemetry.sysmon_reader import is_relevant_proxy_registry_path, normalize_registry_path

ETW_LIMITATION = "ETW adapter is optional and may require elevated privileges or provider-specific configuration."


def etw_supported() -> bool:
    """Return True when platform could host ETW (Windows); does not start a session."""
    return platform.system().lower() == "windows"


def parse_etw_registry_event(raw: dict[str, Any]) -> RegistryWriteEvent | None:
    """Parse fixture ETW-shaped dict rows into registry write events."""
    warnings: list[str] = []
    registry_path = normalize_registry_path(
        str(raw.get("registry_path") or raw.get("TargetObject") or raw.get("ObjectName") or "")
    )
    if not registry_path or not is_relevant_proxy_registry_path(registry_path):
        return None

    ts_raw = raw.get("timestamp_utc") or raw.get("UtcTime") or raw.get("timestamp")
    if ts_raw is None:
        warnings.append("missing_timestamp_defaulted_to_epoch")
        timestamp = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        try:
            timestamp = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError:
            warnings.append(f"unparseable_timestamp:{ts_raw}")
            timestamp = datetime(1970, 1, 1, tzinfo=timezone.utc)

    process_path = str(raw.get("process_path") or raw.get("Image") or "").strip() or None
    pid = raw.get("process_id") or raw.get("ProcessId")
    process_id = int(pid) if pid is not None and str(pid).isdigit() else None
    if process_id is None:
        warnings.append("missing_process_id")
    if not process_path:
        warnings.append("missing_process_path")

    return RegistryWriteEvent(
        timestamp_utc=timestamp,
        source="etw",
        event_id=raw.get("event_id"),
        registry_path=registry_path,
        registry_value_name=raw.get("registry_value_name") or registry_path.rsplit("\\", 1)[-1],
        registry_value_data=str(raw.get("registry_value_data") or raw.get("Details") or "") or None,
        process_guid=str(raw.get("process_guid") or "") or None,
        process_id=process_id,
        process_name=(process_path.rsplit("\\", 1)[-1] if process_path else None),
        process_path=process_path,
        command_line=str(raw.get("command_line") or "") or None,
        user=str(raw.get("user") or "") or None,
        raw_event=dict(raw),
        parse_warnings=warnings,
    )

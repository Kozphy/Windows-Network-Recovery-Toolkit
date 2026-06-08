"""Parse Sysmon Event ID 13 (registry value set) rows from dict fixtures."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from telemetry.models import PROXY_REGISTRY_VALUE_NAMES, RegistryWriteEvent

_INTERNET_SETTINGS_NEEDLE = r"internet settings"
_PROXY_VALUE_PATTERN = re.compile(
    r"(?i)(proxyenable|proxyserver|autoconfigurl|proxyoverride)(?:\\|$)"
)


def normalize_registry_path(path: str) -> str:
    """Normalize registry path separators and casing for comparisons."""
    normalized = str(path or "").strip().replace("/", "\\")
    if normalized.upper().startswith("HKEY_CURRENT_USER\\"):
        normalized = "HKCU\\" + normalized[len("HKEY_CURRENT_USER\\") :]
    return normalized


def is_relevant_proxy_registry_path(path: str) -> bool:
    """Return True when path targets WinINET proxy registry values."""
    normalized = normalize_registry_path(path)
    lower = normalized.lower()
    if _INTERNET_SETTINGS_NEEDLE not in lower:
        return False
    if _PROXY_VALUE_PATTERN.search(normalized):
        return True
    tail = normalized.rsplit("\\", 1)[-1]
    return tail in PROXY_REGISTRY_VALUE_NAMES


def _coerce_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_timestamp(raw: dict[str, Any], warnings: list[str]) -> datetime:
    for key in ("UtcTime", "utc_time", "TimeCreated", "timestamp", "timestamp_utc"):
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


def _extract_value_name(target_object: str) -> str | None:
    normalized = normalize_registry_path(target_object)
    if not normalized:
        return None
    tail = normalized.rsplit("\\", 1)[-1]
    if tail in PROXY_REGISTRY_VALUE_NAMES:
        return tail
    return None


def _extract_process_name(image: str | None) -> str | None:
    if not image:
        return None
    return image.rsplit("\\", 1)[-1] or None


def parse_sysmon_registry_event(raw: dict[str, Any]) -> RegistryWriteEvent | None:
    """Parse one Sysmon-style registry set event; return None when not EID 13."""
    warnings: list[str] = []
    event_id = _coerce_int(raw.get("EventID") or raw.get("Id") or raw.get("event_id"))
    if event_id != 13:
        return None

    target_object = str(
        raw.get("TargetObject") or raw.get("target_object") or raw.get("RegistryPath") or ""
    ).strip()
    if not target_object:
        warnings.append("missing_target_object")

    image = str(raw.get("Image") or raw.get("ProcessPath") or raw.get("image") or "").strip()
    if not image:
        warnings.append("missing_image")
    process_id = _coerce_int(raw.get("ProcessId") or raw.get("ProcessID") or raw.get("pid"))
    if process_id is None:
        warnings.append("missing_process_id")

    details = raw.get("Details") or raw.get("details")
    details_text = None if details is None else str(details)

    return RegistryWriteEvent(
        timestamp_utc=_parse_timestamp(raw, warnings),
        source="sysmon",
        event_id=13,
        registry_path=normalize_registry_path(target_object),
        registry_value_name=_extract_value_name(target_object),
        registry_value_data=details_text,
        process_guid=str(raw.get("ProcessGuid") or raw.get("process_guid") or "") or None,
        process_id=process_id,
        process_name=_extract_process_name(image),
        process_path=image or None,
        command_line=str(raw.get("CommandLine") or raw.get("command_line") or "") or None,
        user=str(raw.get("User") or raw.get("user") or "") or None,
        raw_event=dict(raw),
        parse_warnings=warnings,
    )


def parse_sysmon_fixture_file(events: list[dict[str, Any]]) -> list[RegistryWriteEvent]:
    """Parse a list of raw Sysmon dict rows into registry write events."""
    parsed: list[RegistryWriteEvent] = []
    for row in events:
        event = parse_sysmon_registry_event(row)
        if event is not None:
            parsed.append(event)
    return parsed

"""Audit timeline builder from .audit/ JSONL files."""

from __future__ import annotations

from typing import Any

from windows_network_toolkit.audit_store import read_audit_logs


def build_proxy_timeline(*, audit_dir_pattern: str = "*.jsonl") -> dict[str, Any]:
    rows = read_audit_logs(pattern=audit_dir_pattern)
    ordered = sorted(rows, key=lambda r: str(r.get("timestamp_utc") or ""))
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in ordered:
        cmd = str(row.get("command") or row.get("event") or "unknown")
        groups.setdefault(cmd, []).append(row)
    return {
        "event_count": len(ordered),
        "timeline": ordered,
        "groups": {k: len(v) for k, v in groups.items()},
    }

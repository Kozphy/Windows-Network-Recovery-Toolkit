"""Router evidence import and correlation runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .correlator import correlate_host_router
from .importers import IMPORTERS
from .normalizer import write_router_jsonl
from .models import ROUTER_SCHEMA


def run_router_import(
    *,
    import_type: str,
    input_path: str,
    out_path: str,
    inject: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    importer = IMPORTERS.get(import_type)
    if not importer:
        return {"ok": False, "error": f"Unknown import type: {import_type}"}
    events = importer(Path(input_path), inject=inject)
    result = write_router_jsonl(events, Path(out_path))
    result["import_type"] = import_type
    return result


def load_router_jsonl(path: str | Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    p = Path(path)
    if not p.is_file():
        return events
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def run_router_correlation(
    *,
    host_log: str,
    router_log: str,
) -> dict[str, Any]:
    from windows_network_toolkit.diagnostics.lan_privacy.collectors import observations_from_watch_events
    from windows_network_toolkit.diagnostics.lan_privacy.watch import load_watch_jsonl

    host_events = load_watch_jsonl(host_log)
    observations = observations_from_watch_events(host_events)
    devices = host_events[-1].get("devices", []) if host_events else []
    router_events = load_router_jsonl(router_log)
    correlation = correlate_host_router(observations, router_events, devices)
    return {
        "schema_version": ROUTER_SCHEMA,
        "host_observation_count": len(observations),
        "router_event_count": len(router_events),
        "correlation": correlation,
    }

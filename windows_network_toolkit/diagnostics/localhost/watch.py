"""Bounded localhost-watch for listener/TCP/HTTP state transitions."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from windows_network_toolkit import __version__

from .runner import run_localhost_diagnose
from .target import parse_localhost_target

MIN_INTERVAL_SECONDS = 1.0
MAX_DURATION_SECONDS = 3600.0


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _snapshot(
    *,
    url: str | None,
    host: str | None,
    port: int | None,
    path: str | None,
    timeout: float,
    run: Callable[..., Any] | None,
    include_http: bool,
) -> dict[str, Any]:
    report = run_localhost_diagnose(
        url=url,
        host=host,
        port=port,
        path=path,
        timeout=timeout,
        include_http=include_http,
        run=run,
    )
    listeners = (report.get("listeners") or {}).get("listeners") or []
    tcp = report.get("tcp_probes") or []
    http = report.get("http_probes") or []
    pids = sorted({r.get("pid") for r in listeners if r.get("pid") is not None})
    families = sorted({r.get("address_family") for r in listeners if r.get("address_family")})
    any_tcp = any(p.get("connect_success") for p in tcp)
    http_ok = any(h.get("success") for h in http) if http else None
    return {
        "timestamp_utc": _now(),
        "listening": bool(listeners),
        "pids": pids,
        "address_families": families,
        "tcp_connected": any_tcp,
        "http_ok": http_ok,
        "port": (report.get("target") or {}).get("port"),
        "classification": (report.get("classification") or {}).get("code"),
    }


def _transitions(prev: dict[str, Any], cur: dict[str, Any]) -> list[str]:
    events: list[str] = []
    if not prev.get("listening") and cur.get("listening"):
        events.append("CLOSED_TO_LISTENING")
    if prev.get("listening") and not cur.get("listening"):
        events.append("LISTENING_TO_CLOSED")
    if prev.get("pids") and cur.get("pids") and prev.get("pids") != cur.get("pids"):
        events.append("PID_CHANGED")
    if prev.get("address_families") != cur.get("address_families") and (
        prev.get("listening") or cur.get("listening")
    ):
        events.append("IPV4_IPV6_BINDING_CHANGED")
    if prev.get("http_ok") is not None and cur.get("http_ok") is not None and prev.get("http_ok") != cur.get("http_ok"):
        events.append("HTTP_HEALTH_CHANGED")
    # Weak port replacement signal only when closed on target and something else changed externally — watch stays on one port
    return events


def run_localhost_watch(
    *,
    url: str | None = None,
    host: str | None = None,
    port: int | None = None,
    path: str | None = None,
    interval: float = 2.0,
    duration: float = 60.0,
    timeout: float = 2.0,
    include_http: bool = False,
    jsonl_out: str | Path | None = None,
    run: Callable[..., Any] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Watch a localhost target for state transitions within a bounded window."""

    if interval < MIN_INTERVAL_SECONDS:
        raise ValueError(f"interval must be >= {MIN_INTERVAL_SECONDS}")
    if duration <= 0 or duration > MAX_DURATION_SECONDS:
        raise ValueError(f"duration must be in (0, {MAX_DURATION_SECONDS}]")

    target = parse_localhost_target(url=url, host=host, port=port, path=path)
    watch_id = f"lw-{uuid.uuid4().hex[:12]}"
    deadline = monotonic_fn() + duration
    events: list[dict[str, Any]] = []
    prev = _snapshot(
        url=url,
        host=host,
        port=port,
        path=path,
        timeout=timeout,
        run=run,
        include_http=include_http,
    )
    out_path = Path(jsonl_out) if jsonl_out else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    def _emit(row: dict[str, Any]) -> None:
        events.append(row)
        if out_path:
            with out_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    _emit(
        {
            "event": "watch_started",
            "watch_id": watch_id,
            "timestamp_utc": _now(),
            "target": target.to_dict(),
            "interval": interval,
            "duration": duration,
            "tool_version": __version__,
            "snapshot": prev,
        }
    )

    while monotonic_fn() < deadline:
        remaining = deadline - monotonic_fn()
        if remaining <= 0:
            break
        sleep_fn(min(interval, remaining))
        cur = _snapshot(
            url=url,
            host=host,
            port=port,
            path=path,
            timeout=timeout,
            run=run,
            include_http=include_http,
        )
        for name in _transitions(prev, cur):
            _emit(
                {
                    "event": name,
                    "watch_id": watch_id,
                    "timestamp_utc": _now(),
                    "before": prev,
                    "after": cur,
                    "limitations": [
                        "Transitions are observational; PORT_REPLACEMENT_POSSIBLE requires nearby-listener corroboration outside single-port watch.",
                    ],
                }
            )
        prev = cur

    summary = {
        "schema_version": "wnt.localhost_watch.v1",
        "command": "localhost-watch",
        "watch_id": watch_id,
        "timestamp_utc": _now(),
        "target": target.to_dict(),
        "interval": interval,
        "duration": duration,
        "events_emitted": len(events),
        "final_snapshot": prev,
        "jsonl_out": str(out_path) if out_path else None,
        "tool_version": __version__,
        "policy": {"decision": "PREVIEW", "dry_run": True},
        "limitations": [
            "Watch is read-only and does not restart applications or change firewall/proxy settings.",
        ],
    }
    return summary

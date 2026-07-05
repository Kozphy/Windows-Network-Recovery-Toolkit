"""Router log importers — vendor-agnostic CSV/JSON parsers.

Module responsibility:
    Parse exported DNS, firewall, DHCP, and device logs into ``RouterEvent`` dicts
    via the ``IMPORTERS`` registry.

System placement:
    Called by ``router_evidence.runner.run_router_import`` and router-import CLI.

Key invariants:
    * Read-only file ingest — no live router API calls from this module.
    * Header normalization supports common vendor CSV column variants.
    * ``inject`` bypasses disk read for tests and fixtures.

Side effects:
    * Reads user-supplied log files from disk during import.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import ROUTER_SCHEMA, RouterEvent, RouterEventType


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eid(*parts: str) -> str:
    return "rt-" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:14]


def _normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_")


def import_dns_log(path: Path, *, inject: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if inject is not None:
        return inject
    events: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if text.startswith("["):
        rows = json.loads(text)
        for row in rows:
            ts = row.get("timestamp") or row.get("timestamp_utc") or _now()
            client = row.get("client_ip") or row.get("client") or ""
            domain = row.get("query") or row.get("domain") or ""
            ev = RouterEvent(
                event_id=_eid(ts, client, domain),
                timestamp_utc=ts,
                event_type=RouterEventType.DNS.value,
                client_ip=client,
                domain=domain,
                query=domain,
                raw=row,
            )
            events.append(ev.to_dict())
        return events

    with path.open(encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            norm = {_normalize_header(k): v for k, v in row.items()}
            ts = norm.get("timestamp") or norm.get("time") or _now()
            client = norm.get("client_ip") or norm.get("client") or norm.get("src_ip") or ""
            domain = norm.get("query") or norm.get("domain") or norm.get("name") or ""
            ev = RouterEvent(
                event_id=_eid(ts, client, domain),
                timestamp_utc=ts,
                event_type=RouterEventType.DNS.value,
                client_ip=client,
                domain=domain,
                query=domain,
                action=norm.get("action", ""),
                raw=norm,
            )
            events.append(ev.to_dict())
    return events


def import_firewall_log(path: Path, *, inject: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if inject is not None:
        return inject
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            norm = {_normalize_header(k): v for k, v in row.items()}
            ts = norm.get("timestamp") or norm.get("time") or _now()
            src = norm.get("src_ip") or norm.get("source") or ""
            dst = norm.get("dst_ip") or norm.get("destination") or ""
            port = int(norm.get("port") or norm.get("dst_port") or 0)
            ev = RouterEvent(
                event_id=_eid(ts, src, dst, str(port)),
                timestamp_utc=ts,
                event_type=RouterEventType.FIREWALL.value,
                src_ip=src,
                dst_ip=dst,
                port=port,
                action=norm.get("action", ""),
                raw=norm,
            )
            events.append(ev.to_dict())
    return events


def import_dhcp_leases(path: Path, *, inject: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if inject is not None:
        return inject
    events: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    rows: list[dict[str, Any]]
    if text.startswith("["):
        rows = json.loads(text)
    else:
        with path.open(encoding="utf-8", errors="replace") as f:
            rows = list(csv.DictReader(f))
    for row in rows:
        norm = {_normalize_header(k): v for k, v in row.items()}
        mac = norm.get("mac") or norm.get("mac_address") or ""
        ip = norm.get("ip") or norm.get("ip_address") or ""
        hostname = norm.get("hostname") or norm.get("name") or ""
        ts = norm.get("lease_start") or norm.get("timestamp") or _now()
        ev = RouterEvent(
            event_id=_eid(mac, ip),
            timestamp_utc=ts,
            event_type=RouterEventType.DHCP.value,
            mac=mac,
            client_ip=ip,
            hostname=hostname,
            raw=norm,
        )
        events.append(ev.to_dict())
    return events


def import_device_list(path: Path, *, inject: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if inject is not None:
        return inject
    data = json.loads(path.read_text(encoding="utf-8"))
    devices = data if isinstance(data, list) else data.get("devices", [])
    events: list[dict[str, Any]] = []
    for row in devices:
        mac = row.get("mac", "")
        ip = row.get("ip", "")
        ev = RouterEvent(
            event_id=_eid(mac, ip),
            timestamp_utc=_now(),
            event_type=RouterEventType.DEVICE.value,
            mac=mac,
            client_ip=ip,
            hostname=row.get("name") or row.get("hostname", ""),
            raw=row,
        )
        events.append(ev.to_dict())
    return events


IMPORTERS = {
    "dns": import_dns_log,
    "firewall": import_firewall_log,
    "dhcp": import_dhcp_leases,
    "devices": import_device_list,
}

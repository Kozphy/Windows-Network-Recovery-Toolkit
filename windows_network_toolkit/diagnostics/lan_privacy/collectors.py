"""LAN privacy collectors — inventory, subnet parse, protocol summaries.

Module responsibility:
    Orchestrate neighbor, mDNS, and SSDP probes into ``LanDevice`` / ``LanObservation``
    records and watch-event normalization.

System placement:
    Called by ``lan_privacy.runner``, ``watch``, and ``lan-inventory`` / probe CLI paths.

Key invariants:
    * Delegates live probes to ``src.observability.*`` — no duplicate socket logic.
    * ``inject`` parameters preserve testability without Windows network I/O.
    * Every collection payload includes schema version and limitation strings.

Side effects:
    * Read-only subprocess and UDP probes on Windows when not using ``inject``.
"""

from __future__ import annotations

import hashlib
import ipaddress
import platform
import re
import socket
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from src.observability.lan_neighbor import collect_lan_neighbors
from src.observability.mdns_probe import probe_mdns
from src.observability.ssdp_probe import probe_ssdp

from .models import SCHEMA_VERSION, LanDevice, LanObservation
from .oui_lookup import is_iot_like_vendor, lookup_vendor

_SUBNET_RE = re.compile(r"IPv4 Address[^:]*:\s*(\d+\.\d+\.\d+\.\d+)", re.I)
_MASK_RE = re.compile(r"Subnet Mask[^:]*:\s*(\d+\.\d+\.\d+\.\d+)", re.I)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _event_id(*parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
    return f"lan-{h}"


def parse_local_subnet(
    *,
    run: Callable[..., Any] | None = None,
    timeout: float = 15.0,
    inject: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if inject is not None:
        return inject
    if platform.system().lower() != "windows":
        return {"ok": False, "subnet": "", "limitations": ["Subnet parse requires Windows or fixture."]}
    run_fn = run or subprocess.run
    try:
        proc = run_fn(["ipconfig"], capture_output=True, text=True, timeout=timeout, check=False)
        text = proc.stdout or ""
        ip_match = _SUBNET_RE.search(text)
        mask_match = _MASK_RE.search(text)
        if ip_match and mask_match:
            iface = ipaddress.IPv4Interface(f"{ip_match.group(1)}/{mask_match.group(1)}")
            return {
                "ok": True,
                "subnet": str(iface.network),
                "host_ip": ip_match.group(1),
                "limitations": [],
            }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return {"ok": False, "subnet": "", "limitations": ["Could not parse local subnet from ipconfig."]}


def _resolve_hostname(ip: str) -> str:
    try:
        name, _, _ = socket.getnameinfo((ip, 0), 0)
        if name and name != ip:
            return name
    except (socket.gaierror, OSError):
        pass
    return ""


def collect_inventory(
    *,
    run: Callable[..., Any] | None = None,
    timeout: float = 20.0,
    subnet_override: str = "",
    inject: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enumerate LAN devices from neighbor table with OUI lookup."""
    if inject is not None:
        devices = [LanDevice(**d) if isinstance(d, dict) else d for d in inject.get("devices", [])]
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "timestamp_utc": _now(),
            "subnet": inject.get("subnet", ""),
            "devices": [d.to_dict() if hasattr(d, "to_dict") else d for d in devices],
            "limitations": inject.get("limitations", []),
        }

    subnet_info = parse_local_subnet(run=run, timeout=timeout)
    neighbor = collect_lan_neighbors(run=run, timeout=timeout)
    now = _now()
    devices: list[dict[str, Any]] = []
    for row in neighbor.get("devices") or []:
        ip = row.get("ip", "")
        mac = row.get("mac", "")
        vendor, known = lookup_vendor(mac)
        hostname = _resolve_hostname(ip) if ip else ""
        flags: list[str] = []
        if not known:
            flags.append("unknown_vendor")
        if not hostname:
            flags.append("missing_hostname")
        if is_iot_like_vendor(vendor):
            flags.append("iot_like")
        devices.append(
            LanDevice(
                ip=ip,
                mac=mac,
                hostname=hostname,
                vendor=vendor,
                vendor_known=known,
                first_seen_utc=now,
                last_seen_utc=now,
                flags=flags,
            ).to_dict()
        )

    limitations = list(neighbor.get("limitations") or []) + list(subnet_info.get("limitations") or [])
    limitations.append("Inventory reflects ARP/neighbor cache — not authoritative DHCP roster.")

    return {
        "ok": neighbor.get("ok", False),
        "schema_version": SCHEMA_VERSION,
        "timestamp_utc": now,
        "subnet": subnet_override or subnet_info.get("subnet", ""),
        "devices": devices,
        "limitations": limitations,
    }


def collect_mdns_summary(
    *,
    duration_seconds: float = 5.0,
    inject: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = probe_mdns(duration_seconds=duration_seconds, inject=inject)
    result["summary"] = "observed local network discovery activity (mDNS)"
    return result


def collect_ssdp_summary(
    *,
    duration_seconds: float = 5.0,
    inject: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = probe_ssdp(duration_seconds=duration_seconds, inject=inject)
    result["summary"] = "observed local network discovery activity (SSDP/UPnP)"
    return result


def observations_from_watch_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert lan-watch JSONL rows to LanObservation dicts."""
    out: list[dict[str, Any]] = []
    for ev in events:
        ts = ev.get("timestamp_utc") or ev.get("timestamp") or _now()
        for obs in ev.get("observations") or []:
            proto = obs.get("protocol", "ARP")
            eid = _event_id(ts, proto, obs.get("source_ip", ""), obs.get("target_ip", ""))
            out.append(
                LanObservation(
                    event_id=eid,
                    timestamp_utc=ts,
                    protocol=proto,
                    source_ip=obs.get("source_ip", ""),
                    source_mac=obs.get("source_mac", ""),
                    target_ip=obs.get("target_ip", ""),
                    target_port=int(obs.get("target_port") or 0),
                    direction=obs.get("direction", "broadcast"),
                    evidence_source=obs.get("evidence_source", "HOST_LEVEL_OBSERVATION"),
                    raw=obs,
                ).to_dict()
            )
    return out

"""Map localhost proxy ports to listening PIDs and process names (read-only)."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


def _run_argv(argv: list[str], timeout: float = 45.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


_LOCAL_HOST_PAT = re.compile(
    r"^(127\.(?:\d{1,3}\.){2}\d{1,3}|localhost)\:(\d{1,5})\s*$",
    re.IGNORECASE,
)


def parse_local_proxy_server(proxy_server: str | None) -> tuple[str | None, int | None]:
    """If ``proxy_server`` is ``host:port`` for loopback, return ``(host, port)``."""

    if not proxy_server:
        return None, None
    s = proxy_server.strip().split(";")[0].strip()
    m = _LOCAL_HOST_PAT.match(s)
    if not m:
        return None, None
    host, port_s = m.group(1).lower(), int(m.group(2))
    return host, port_s


def _parse_netstat_listeners(netstat_out: str, target_port: int) -> list[dict[str, Any]]:
    """Find LISTENING rows for ``127.0.0.1:target_port`` or ``0.0.0.0:target_port``."""

    hits: list[dict[str, Any]] = []
    for line in netstat_out.splitlines():
        line = line.strip()
        if not line or line.startswith("Active") or "---" in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        proto = parts[0].upper()
        if proto != "TCP":
            continue
        local = parts[1]
        state = parts[3] if len(parts) >= 5 else ""
        pid = parts[-1]
        if state != "LISTENING":
            continue
        lp = _local_port(local)
        if lp is None or lp != target_port:
            continue
        if local.startswith("127.") or local.startswith("[::1]"):
            prio = 0
        elif local.startswith("0.0.0.0:") or local.startswith("[::]:"):
            prio = 1
        else:
            prio = 2
        hits.append(
            (
                prio,
                {
                    "proto": proto,
                    "local_address": local,
                    "listening_state": state,
                    "pid": int(pid) if pid.isdigit() else None,
                },
            )
        )
    hits.sort(key=lambda x: x[0])
    return [h[1] for h in hits]


def _local_port(local: str) -> int | None:
    """Extract numeric port from ``netstat`` local endpoint (IPv4 or IPv6)."""

    if local.startswith("["):
        m = re.search(r"\]:(\d{1,5})\s*$", local)
    else:
        _a, _, ps = local.rpartition(":")
        m = re.match(r"^(\d{1,5})$", ps)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def pid_to_process_name(pid: int) -> str | None:
    """Resolve PID to image name via ``tasklist`` (Windows)."""

    if sys.platform != "win32" or pid <= 0:
        return None
    code, out = _run_argv(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        timeout=20.0,
    )
    if code != 0:
        return None
    # "image.exe","1234",...
    first = out.strip().splitlines()[0] if out.strip() else ""
    if not first:
        return None
    m = re.match(r'"([^"]+)"', first)
    if m:
        return m.group(1)
    return first.split(",")[0].strip('"')


def map_local_proxy_port(proxy_server: str | None) -> dict[str, Any] | None:
    """Resolve localhost ``ProxyServer`` to owning process if listening.

    Returns:
        Dict with ``process_name``, ``pid``, ``listening_state``, or ``None`` if not applicable.
    """

    _host, port = parse_local_proxy_server(proxy_server)
    if port is None:
        return None

    if sys.platform != "win32":
        return {
            "port": port,
            "process_name": None,
            "pid": None,
            "listening_state": None,
            "note": "netstat mapping skipped on non-Windows",
        }

    code, nout = _run_argv(["netstat", "-ano"], timeout=45.0)
    if code != 0:
        return {
            "port": port,
            "process_name": None,
            "pid": None,
            "listening_state": None,
            "note": f"netstat failed: {nout[:200]}",
        }

    hits = _parse_netstat_listeners(nout, port)
    if not hits:
        return {
            "port": port,
            "process_name": None,
            "pid": None,
            "listening_state": "NOT_FOUND",
        }

    best = hits[0]
    pid = best.get("pid")
    pname = pid_to_process_name(pid) if pid else None
    return {
        "port": port,
        "process_name": pname,
        "pid": pid,
        "listening_state": best.get("listening_state"),
        "local_address": best.get("local_address"),
    }


@dataclass(frozen=True)
class PortOwner:
    """Owning listener for a localhost proxy port."""

    port: int | None
    process_name: str | None
    pid: int | None
    listening_state: str | None

"""Injectable read-only probes for bad-gateway diagnosis.

Module responsibility:
    Run DNS, TCP, HTTP (system proxy vs direct), WinINET registry, local listener probes.

System placement:
    Used by ``runner.collect`` path via ``collect_all``.

Key invariants:
    * Injectable ``run`` for tests.
    * Missing curl/PowerShell yields probe failures captured in probe dicts.

Side effects:
    Subprocess and network I/O only; no registry writes.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from windows_network_toolkit.collectors.proxy_registry_collector import collect_proxy_registry


def _run_cmd(argv: list[str], *, run: Callable[..., Any], timeout: float) -> tuple[int, str]:
    try:
        proc = run(argv, capture_output=True, text=True, shell=False, timeout=timeout)
        return int(proc.returncode), ((proc.stdout or "") + (proc.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def probe_dns(host: str, *, run: Callable[..., Any], timeout: float = 15.0) -> dict[str, Any]:
    code, out = _run_cmd(["nslookup", host], run=run, timeout=timeout)
    addresses = re.findall(r"Address:\s*(\S+)", out)
    return {"ok": code == 0 and bool(addresses), "addresses": addresses, "raw_excerpt": out[:500]}


def probe_tcp(host: str, port: int, *, run: Callable[..., Any], timeout: float = 15.0) -> dict[str, Any]:
    ps = (
        f"Test-NetConnection -ComputerName {host} -Port {port} "
        f"-WarningAction SilentlyContinue | Select-Object -ExpandProperty TcpTestSucceeded"
    )
    code, out = _run_cmd(
        ["powershell", "-NoProfile", "-Command", ps],
        run=run,
        timeout=timeout,
    )
    ok = "true" in out.lower()
    return {"ok": ok if code == 0 else False, "host": host, "port": port, "raw": out[:200]}


def _parse_http_status(code: int, out: str) -> int | None:
    if code != 0:
        return None
    m = re.search(r"(\d{3})\s*$", out.strip())
    return int(m.group(1)) if m else None


def probe_http(
    url: str,
    *,
    via_system_proxy: bool,
    run: Callable[..., Any],
    timeout: float = 15.0,
) -> dict[str, Any]:
    argv = [
        "curl",
        "-sS",
        "-o",
        "NUL",
        "-w",
        "%{http_code}",
        "-L",
        "--max-time",
        str(int(timeout)),
    ]
    if not via_system_proxy:
        argv.extend(["--noproxy", "*"])
    argv.append(url)
    code, out = _run_cmd(argv, run=run, timeout=timeout + 5)
    status = _parse_http_status(code, out)
    return {
        "ok": status is not None and status < 500,
        "status_code": status,
        "via_system_proxy": via_system_proxy,
        "curl_exit": code,
    }


def collect_winhttp(*, run: Callable[..., Any], timeout: float = 15.0) -> dict[str, Any]:
    code, out = _run_cmd(["netsh", "winhttp", "show", "proxy"], run=run, timeout=timeout)
    lower = out.lower()
    return {
        "ok": code == 0,
        "direct_access": "direct access" in lower and "no proxy server" in lower,
        "raw": out[:800],
    }


def collect_wininet(*, run: Callable[..., Any] | None = None) -> dict[str, Any]:
    snap = collect_proxy_registry(run=run)
    return {
        "proxy_enable": snap.get("proxy_enable"),
        "proxy_server": snap.get("proxy_server"),
        "auto_config_url": snap.get("auto_config_url"),
    }


def _localhost_port(proxy_server: str | None) -> int | None:
    if not proxy_server:
        return None
    m = re.search(r"127(?:\.\d{1,3}){3}|localhost", proxy_server, re.I)
    if not m:
        return None
    pm = re.search(r":(\d{1,5})", proxy_server)
    return int(pm.group(1)) if pm else None


def resolve_local_proxy_process(
    proxy_server: str | None,
    *,
    run: Callable[..., Any],
) -> dict[str, Any]:
    port = _localhost_port(proxy_server)
    if port is None:
        return {"detected": False, "port": None, "process": None}
    needle = f"127.0.0.1:{port}"
    code, out = _run_cmd(["netstat", "-ano"], run=run, timeout=20.0)
    pid = None
    if code == 0:
        for line in out.splitlines():
            if "LISTENING" in line.upper() and needle in line:
                parts = line.split()
                if parts:
                    try:
                        pid = int(parts[-1])
                    except ValueError:
                        pid = None
                break
    process_name = ""
    if pid:
        tcode, tout = _run_cmd(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            run=run,
            timeout=10.0,
        )
        if tcode == 0:
            process_name = tout.split(",")[0].strip('"')
    return {
        "detected": pid is not None,
        "port": port,
        "process": {"pid": pid, "name": process_name or "unknown"},
        "proof_level": "CORRELATED",
    }


def collect_all(
    url: str,
    *,
    run: Callable[..., Any],
    timeout: float = 15.0,
    inject: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect probes; inject overrides for tests."""
    if inject:
        return inject
    target = urlparse(url)
    host = target.hostname or ""
    port = target.port or (443 if target.scheme == "https" else 80)
    wininet = collect_wininet(run=run)
    return {
        "url": url,
        "dns": probe_dns(host, run=run, timeout=timeout),
        "tcp": probe_tcp(host, port, run=run, timeout=timeout),
        "http_system_proxy": probe_http(url, via_system_proxy=True, run=run, timeout=timeout),
        "http_direct": probe_http(url, via_system_proxy=False, run=run, timeout=timeout),
        "wininet_proxy": wininet,
        "winhttp_proxy": collect_winhttp(run=run, timeout=timeout),
        "local_proxy_process": resolve_local_proxy_process(
            str(wininet.get("proxy_server") or ""),
            run=run,
        ),
    }

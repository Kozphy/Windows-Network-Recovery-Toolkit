"""Proxy-specific read-only probes for layer-aware diagnostics.

Module responsibility:
    Collect WinHTTP/WinINET proxy settings and localhost-listener hints used by layer decisions.

System placement:
    Called from :mod:`failure_system.layer_probe` to enrich generic network probes with proxy-path
    context before classification.

Key invariants:
    - Registry and netstat checks are read-only.
    - Localhost listener correlation is heuristic; never treated as writer proof.
    - Missing values are represented as ``None`` instead of raising errors.
"""

from __future__ import annotations

import re
import subprocess
from typing import Any


_INTERNET_SETTINGS_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _run(argv: list[str], timeout: float = 20.0) -> tuple[int, str]:
    """Execute one proxy-related command and return merged output."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _reg_value(name: str) -> str | None:
    """Read one WinINET HKCU registry value as text.

    Args:
        name: Registry value name under ``Internet Settings``.

    Returns:
        str | None: Parsed value string or ``None`` when query fails/missing.
    """
    code, out = _run(["reg", "query", _INTERNET_SETTINGS_KEY, "/v", name])
    if code != 0:
        return None
    # Typical format: <name> <type> <value>
    for line in out.splitlines():
        if name.lower() not in line.lower():
            continue
        parts = line.split()
        if len(parts) >= 3:
            return " ".join(parts[2:]).strip()
    return None


def _parse_proxy_server(server: str | None) -> tuple[bool, int | None]:
    """Parse localhost proxy host/port hint from WinINET ``ProxyServer`` text."""
    if not server:
        return False, None
    text = server.strip()
    # Supports host:port and http=host:port;https=host:port forms.
    pairs = re.findall(r"(?:^|;)\s*(?:[a-zA-Z]+=\s*)?([^;=]+)", text)
    for seg in pairs:
        m = re.search(r"(?P<host>localhost|127(?:\.\d{1,3}){3}|::1)\s*:\s*(?P<port>\d{1,5})", seg, re.I)
        if m:
            return True, int(m.group("port"))
    return False, None


def _localhost_listener(port: int | None) -> bool | None:
    """Check whether localhost proxy port currently has a listening socket."""
    if port is None:
        return None
    code, out = _run(["netstat", "-ano"], timeout=20.0)
    if code != 0:
        return None
    needle4 = f"127.0.0.1:{port}"
    needle6 = f"[::1]:{port}"
    for line in out.splitlines():
        lower = line.lower()
        if "listen" not in lower:
            continue
        if needle4 in line or needle6 in line or f"localhost:{port}" in lower:
            return True
    return False


def collect_proxy_signals() -> dict[str, Any]:
    """Collect WinHTTP/WinINET proxy state and local listener hints.

    Returns:
        dict[str, Any]: Proxy signal bundle consumed by layer probe and decision modules.

    Side effects:
        Executes ``netsh``, ``reg query``, and ``netstat`` commands.

    Failure modes:
        Command failures degrade to ``*_ok=False`` or ``None`` listener/value fields.

    Audit Notes:
        ``localhost_listener_found=True`` indicates correlation only, not proof of registry writer.
    """
    winhttp_code, winhttp_out = _run(["netsh", "winhttp", "show", "proxy"])
    winhttp_direct = "direct access (no proxy server)" in winhttp_out.lower()
    proxy_enable_raw = _reg_value("ProxyEnable")
    proxy_enable = None
    if proxy_enable_raw is not None:
        try:
            proxy_enable = int(proxy_enable_raw, 0)
        except ValueError:
            proxy_enable = None
    proxy_server = _reg_value("ProxyServer")
    auto_config_url = _reg_value("AutoConfigURL")
    is_localhost_proxy, localhost_port = _parse_proxy_server(proxy_server)
    listener = _localhost_listener(localhost_port)
    return {
        "winhttp_show_proxy_ok": winhttp_code == 0,
        "winhttp_direct": winhttp_direct,
        "wininet_proxy_enable": proxy_enable,
        "wininet_proxy_server": proxy_server,
        "wininet_auto_config_url": auto_config_url,
        "is_localhost_proxy": is_localhost_proxy,
        "localhost_proxy_port": localhost_port,
        "localhost_listener_found": listener,
    }


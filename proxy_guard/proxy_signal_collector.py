"""Windows proxy signal collector (read-only).

Collects WinINET proxy settings and parses localhost proxy endpoints. This module never mutates
registry state and uses subprocess calls with ``shell=False`` only.
"""

from __future__ import annotations

import platform
import re
import subprocess
from typing import Any

INTERNET_SETTINGS_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _run(argv: list[str], timeout_seconds: float = 20.0) -> tuple[int, str]:
    """Execute one command and return merged stdout/stderr text."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _reg_value(name: str) -> str | None:
    """Read one HKCU WinINET registry value.

    Args:
        name: Registry value name under ``INTERNET_SETTINGS_KEY``.

    Returns:
        String value when found, else ``None``.
    """
    code, out = _run(["reg", "query", INTERNET_SETTINGS_KEY, "/v", name])
    if code != 0:
        return None
    for line in out.splitlines():
        if name.lower() not in line.lower():
            continue
        parts = line.split()
        if len(parts) >= 3:
            return " ".join(parts[2:]).strip()
    return None


def parse_proxy_server(proxy_server: str | None) -> dict[str, Any]:
    """Parse WinINET ProxyServer for localhost endpoint hints."""
    if not proxy_server:
        return {
            "raw": proxy_server,
            "is_localhost_proxy": False,
            "localhost_host": None,
            "localhost_port": None,
        }
    text = proxy_server.strip()
    # Accept host:port or scheme=host:port;scheme2=host:port
    segments = re.findall(r"(?:^|;)\s*(?:[a-zA-Z]+=\s*)?([^;=]+)", text)
    for seg in segments:
        m = re.search(r"(?P<host>localhost|127(?:\.\d{1,3}){3}|::1)\s*:\s*(?P<port>\d{1,5})", seg, re.I)
        if not m:
            continue
        return {
            "raw": proxy_server,
            "is_localhost_proxy": True,
            "localhost_host": m.group("host"),
            "localhost_port": int(m.group("port")),
        }
    return {
        "raw": proxy_server,
        "is_localhost_proxy": False,
        "localhost_host": None,
        "localhost_port": None,
    }


def collect_proxy_signals() -> dict[str, Any]:
    """Collect WinINET proxy posture for diagnostics.

    Returns:
        Dict containing ``ProxyEnable``, ``ProxyServer``, ``AutoConfigURL`` and parsed localhost
        endpoint hints.
    """
    is_windows = platform.system().lower() == "windows"
    if not is_windows:
        return {
            "platform": platform.system(),
            "proxy_enable": None,
            "proxy_server": None,
            "auto_config_url": None,
            "parsed_proxy": parse_proxy_server(None),
            "limitations": ["non_windows_platform"],
        }
    proxy_enable_raw = _reg_value("ProxyEnable")
    proxy_enable: int | None = None
    if proxy_enable_raw is not None:
        try:
            proxy_enable = int(proxy_enable_raw, 0)
        except ValueError:
            proxy_enable = None
    proxy_server = _reg_value("ProxyServer")
    auto_config_url = _reg_value("AutoConfigURL")
    return {
        "platform": "Windows",
        "proxy_enable": proxy_enable,
        "proxy_server": proxy_server,
        "auto_config_url": auto_config_url,
        "parsed_proxy": parse_proxy_server(proxy_server),
        "limitations": [],
    }


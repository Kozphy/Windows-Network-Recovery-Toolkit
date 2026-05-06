"""Windows WinINET proxy signal collector.

This module is the observation layer for the proxy risk engine. It reads browser-facing WinINET
proxy configuration from HKCU and parses proxy endpoints for loopback routing indicators.

Safety boundary:
    Read-only collection only. This module never modifies registry values.
"""

from __future__ import annotations

import ipaddress
import logging
import platform
import re
import subprocess
from typing import Any
from urllib.parse import urlparse

INTERNET_SETTINGS_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_LOGGER = logging.getLogger(__name__)
_LOCALHOST_NAMES = {"localhost"}
_REG_VALUE_NAMES = ("ProxyEnable", "ProxyServer", "AutoConfigURL")


def _is_windows() -> bool:
    """Return whether this process is running on Windows."""
    return platform.system().lower() == "windows"


def _run(argv: list[str], timeout_seconds: float = 20.0) -> tuple[int, str]:
    """Execute one command and return merged stdout/stderr text.

    Args:
        argv: Command arguments passed with ``shell=False``.
        timeout_seconds: Maximum runtime for the command.

    Returns:
        Tuple of return code and merged output text.
    """
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            shell=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _LOGGER.debug("Command failed while collecting proxy signal: %s", exc)
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _read_registry_with_winreg(name: str) -> Any | None:
    """Read a WinINET registry value using the Python standard library.

    Args:
        name: Registry value under ``INTERNET_SETTINGS_KEY``.

    Returns:
        Native registry value when found, otherwise ``None``.
    """
    if not _is_windows():
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            value, _value_type = winreg.QueryValueEx(key, name)
            return value
    except (FileNotFoundError, OSError, ImportError):
        return None


def _reg_value(name: str) -> str | None:
    """Read one HKCU WinINET registry value as text.

    Args:
        name: Registry value name under ``INTERNET_SETTINGS_KEY``.

    Returns:
        String value when found, else ``None``.
    """
    native_value = _read_registry_with_winreg(name)
    if native_value is not None:
        return str(native_value)

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


def _parse_int(value: str | None) -> int | None:
    """Parse a registry integer value from decimal or hexadecimal text."""
    if value is None:
        return None
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return None


def _is_loopback_host(host: str | None) -> bool:
    """Return whether host is localhost or a loopback IP address."""
    if not host:
        return False
    normalized = host.strip().strip("[]").lower()
    if normalized in _LOCALHOST_NAMES:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _valid_port(port: int | None) -> bool:
    """Return whether a TCP port is in the valid user-observable range."""
    return port is not None and 0 < port <= 65535


def _parse_endpoint(segment: str) -> dict[str, Any] | None:
    """Parse one WinINET proxy segment into an endpoint dictionary.

    Args:
        segment: Raw segment such as ``http=127.0.0.1:8080`` or ``[::1]:8888``.

    Returns:
        Endpoint dictionary, or ``None`` when no host/port can be parsed.
    """
    raw = segment.strip()
    if not raw:
        return None

    scheme: str | None = None
    target = raw
    if "=" in raw and "://" not in raw.split("=", 1)[0]:
        scheme, target = raw.split("=", 1)
        scheme = scheme.strip().lower() or None
        target = target.strip()

    parse_target = target
    if "://" not in parse_target:
        parse_target = f"//{parse_target}"

    parsed = urlparse(parse_target)
    host = parsed.hostname
    try:
        port = parsed.port
    except ValueError:
        port = None
    if host and _valid_port(port):
        return {
            "scheme": scheme or (parsed.scheme if parsed.scheme else None),
            "host": host,
            "port": int(port),
            "is_loopback": _is_loopback_host(host),
            "raw": raw,
        }

    # Fallback for unbracketed ::1:PORT and other unusual but common registry strings.
    ipv6_match = re.match(r"^(?P<host>::1)\s*:\s*(?P<port>\d{1,5})$", target, re.IGNORECASE)
    if ipv6_match and _valid_port(int(ipv6_match.group("port"))):
        return {
            "scheme": scheme,
            "host": ipv6_match.group("host"),
            "port": int(ipv6_match.group("port")),
            "is_loopback": True,
            "raw": raw,
        }

    host_port_match = re.match(r"^(?P<host>localhost|127(?:\.\d{1,3}){3})\s*:\s*(?P<port>\d{1,5})$", target, re.IGNORECASE)
    if host_port_match and _valid_port(int(host_port_match.group("port"))):
        host = host_port_match.group("host")
        return {
            "scheme": scheme,
            "host": host,
            "port": int(host_port_match.group("port")),
            "is_loopback": _is_loopback_host(host),
            "raw": raw,
        }
    return None


def parse_proxy_server(proxy_server: str | None) -> dict[str, Any]:
    """Parse WinINET ``ProxyServer`` text for localhost endpoint hints.

    Args:
        proxy_server: Raw WinINET ``ProxyServer`` registry value.

    Returns:
        Parsed proxy metadata with loopback detection and endpoint details.
    """
    if not proxy_server:
        return {
            "raw": proxy_server,
            "is_localhost_proxy": False,
            "localhost_host": None,
            "localhost_port": None,
            "endpoints": [],
        }
    text = proxy_server.strip()
    segments = [segment for segment in text.split(";") if segment.strip()]
    endpoints = [endpoint for segment in segments if (endpoint := _parse_endpoint(segment)) is not None]
    for endpoint in endpoints:
        if not endpoint.get("is_loopback"):
            continue
        return {
            "raw": proxy_server,
            "is_localhost_proxy": True,
            "localhost_host": endpoint.get("host"),
            "localhost_port": endpoint.get("port"),
            "endpoints": endpoints,
        }
    return {
        "raw": proxy_server,
        "is_localhost_proxy": False,
        "localhost_host": None,
        "localhost_port": None,
        "endpoints": endpoints,
    }


def collect_proxy_signals() -> dict[str, Any]:
    """Collect WinINET proxy posture for diagnostics.

    Returns:
        Dict containing ``ProxyEnable``, ``ProxyServer``, ``AutoConfigURL`` and parsed localhost
        endpoint hints.
    """
    if not _is_windows():
        return {
            "platform": platform.system(),
            "registry_key": INTERNET_SETTINGS_KEY,
            "proxy_enable": None,
            "proxy_server": None,
            "auto_config_url": None,
            "parsed_proxy": parse_proxy_server(None),
            "observations": ["WinINET proxy registry was not inspected because platform is not Windows."],
            "limitations": ["non_windows_platform"],
        }

    proxy_enable_raw = _reg_value("ProxyEnable")
    proxy_enable = _parse_int(proxy_enable_raw)
    proxy_server = _reg_value("ProxyServer")
    auto_config_url = _reg_value("AutoConfigURL")
    parsed_proxy = parse_proxy_server(proxy_server)
    observations = [
        f"WinINET ProxyEnable observed: {proxy_enable}",
        f"WinINET ProxyServer observed: {proxy_server or '<empty>'}",
    ]
    if auto_config_url:
        observations.append(f"WinINET AutoConfigURL observed: {auto_config_url}")
    limitations: list[str] = []
    if proxy_enable is None:
        limitations.append("proxy_enable_value_missing_or_unparseable")
    if proxy_enable == 1 and not proxy_server:
        limitations.append("proxy_enabled_without_static_proxy_server")

    return {
        "platform": "Windows",
        "registry_key": INTERNET_SETTINGS_KEY,
        "registry_values_read": list(_REG_VALUE_NAMES),
        "proxy_enable": proxy_enable,
        "proxy_server": proxy_server,
        "auto_config_url": auto_config_url,
        "parsed_proxy": parsed_proxy,
        "observations": observations,
        "limitations": limitations,
    }


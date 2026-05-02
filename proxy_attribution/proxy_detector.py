"""Collect WinINET (HKCU) and WinHTTP proxy configuration via read-only queries."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


def _run_argv(argv: list[str], timeout: float = 30.0) -> tuple[int, str]:
    """Execute argv without shell; return exit code and merged stdout/stderr."""

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


INTERNET_SETTINGS_KEY = (
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
)


def _parse_reg_sz(line_block: str, value_name: str) -> str | None:
    """Extract REG_SZ / REG_EXPAND_SZ value from ``reg query`` output."""

    for line in line_block.splitlines():
        line = line.strip()
        if not line.startswith(value_name):
            continue
        parts = line.split(None, 2)
        if len(parts) >= 3 and parts[1] in ("REG_SZ", "REG_EXPAND_SZ"):
            return parts[2].strip()
    return None


def _parse_reg_dword(block: str, value_name: str) -> int | None:
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith(value_name):
            continue
        m = re.search(r"0x([0-9a-fA-F]+)", line)
        if m:
            return int(m.group(1), 16)
        m2 = re.search(r"\bREG_DWORD\b\s+(\d+)", line)
        if m2:
            return int(m2.group(1), 10)
    return None


def query_registry_value(key_path: str, value_name: str) -> tuple[int | None, str | None]:
    """Return ``(dword_or_none, string_or_none)`` for a registry value.

    DWORD values populate the first element of the tuple; string values the second.
    """

    code, out = _run_argv(["reg", "query", key_path, "/v", value_name])
    if code != 0:
        return None, None
    dw = _parse_reg_dword(out, value_name)
    if dw is not None:
        return dw, None
    sz = _parse_reg_sz(out, value_name)
    return None, sz


def get_wininet_proxy_state() -> dict[str, Any]:
    """Read HKCU WinINET proxy keys (User-level browser-style settings)."""

    pe, _ = query_registry_value(INTERNET_SETTINGS_KEY, "ProxyEnable")
    _, ps = query_registry_value(INTERNET_SETTINGS_KEY, "ProxyServer")
    _, pac = query_registry_value(INTERNET_SETTINGS_KEY, "AutoConfigURL")

    enabled = pe == 1 if pe is not None else False
    proxy_server = (ps or "").strip() or None
    autoconfig = (pac or "").strip() or None

    return {
        "proxy_enable_reg": pe,
        "proxy_enabled": enabled or bool(proxy_server) or bool(autoconfig),
        "proxy_server": proxy_server,
        "auto_config_url": autoconfig,
    }


def get_winhttp_proxy_raw() -> tuple[int, str]:
    """Return ``netsh winhttp show proxy`` exit code and full text."""

    if sys.platform != "win32":
        return 1, ""
    return _run_argv(["netsh", "winhttp", "show", "proxy"])


def summarize_winhttp(stdout: str) -> dict[str, Any]:
    """Infer direct vs proxy-server lines from WinHTTP summary text."""

    lower = stdout.lower()
    direct = "direct access" in lower and "no proxy server" in lower
    proxy_line = None
    for line in stdout.splitlines():
        ls = line.strip()
        if "proxy server" in ls.lower() and ":" in ls:
            proxy_line = ls
            break
    return {
        "raw": stdout.strip(),
        "direct_access": direct,
        "proxy_line": proxy_line,
        "winhttp_summary": "DIRECT" if direct else ("PROXY_CONFIGURED" if proxy_line else "UNKNOWN"),
    }


@dataclass(frozen=True)
class ProxySnapshot:
    """Structured proxy configuration from WinINET + WinHTTP."""

    proxy_enabled: bool
    proxy_server: str | None
    auto_config_url: str | None
    wininet_proxy_enable: int | None
    winhttp_raw: str
    winhttp_direct: bool
    winhttp_proxy_line: str | None
    winhttp_summary: str


def collect_proxy_snapshot() -> ProxySnapshot:
    """Run read-only probes and return a normalized snapshot."""

    wi = get_wininet_proxy_state()
    code, wh_raw = get_winhttp_proxy_raw()
    wh = summarize_winhttp(wh_raw if code == 0 else "")

    return ProxySnapshot(
        proxy_enabled=bool(wi["proxy_enabled"]),
        proxy_server=wi.get("proxy_server"),
        auto_config_url=wi.get("auto_config_url"),
        wininet_proxy_enable=wi.get("proxy_enable_reg"),
        winhttp_raw=wh_raw.strip(),
        winhttp_direct=wh["direct_access"],
        winhttp_proxy_line=wh.get("proxy_line"),
        winhttp_summary=str(wh.get("winhttp_summary", "UNKNOWN")),
    )

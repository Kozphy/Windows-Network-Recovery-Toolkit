"""HKCU WinINET proxy key reads via ``reg query`` (Windows).

System position:
    Consumed by Proxy Guard CLIs, observability snapshot builder, and watcher loops.

Input assumptions:
    ``reg.exe`` available; path ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings``.

Output guarantees:
    ``ProxyRegistrySnapshot`` uses ``None`` for unreadable values rather than raising.

Failure modes:
    Timeout/OSError surfaces as non-zero codes inside ``read_proxy_registry`` callees via ``_run_reg_query``.

Engineering Notes:
    Keeps parsing logic local to tolerate locale-specific ``reg`` output lines.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from typing import Any

from ..core.models import ProxyRegistrySnapshot

_INTERNET_SETTINGS = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _run_reg_query(value_name: str, run: Callable[..., Any] = subprocess.run) -> tuple[int, str]:
    cmd = ["reg", "query", _INTERNET_SETTINGS, "/v", value_name]
    try:
        proc = run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _parse_reg_dword(text: str) -> int | None:
    for line in text.splitlines():
        line = line.strip()
        if "REG_DWORD" in line:
            m = re.search(r"0x([0-9a-fA-F]+)", line)
            if m:
                return int(m.group(1), 16)
            m2 = re.search(r"REG_DWORD\s+(\d+)", line)
            if m2:
                return int(m2.group(1))
    return None


def _parse_reg_sz(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if "REG_SZ" in line or "REG_EXPAND_SZ" in line:
            parts = line.split(None, 2)
            if len(parts) >= 3:
                return parts[2].strip()
            idx = line.find("REG_SZ")
            if idx == -1:
                idx = line.find("REG_EXPAND_SZ")
            if idx != -1:
                val = line[idx + 6 :].strip() if "REG_SZ" in line else line[idx + 14 :].strip()
                return val or None
    return None


def read_proxy_registry(
    *,
    run: Callable[..., Any] = subprocess.run,
) -> ProxyRegistrySnapshot:
    """Read HKCU WinINET proxy keys via ``reg query`` (Windows).

    Returns:
        Normalized snapshot; failed queries yield ``None`` fields without raising.
    """
    pe_code, pe_out = _run_reg_query("ProxyEnable", run=run)
    ps_code, ps_out = _run_reg_query("ProxyServer", run=run)
    pac_code, pac_out = _run_reg_query("AutoConfigURL", run=run)
    ad_code, ad_out = _run_reg_query("AutoDetect", run=run)

    proxy_enable = _parse_reg_dword(pe_out) if pe_code == 0 else None
    proxy_server = _parse_reg_sz(ps_out) if ps_code == 0 else None
    auto_config_url = _parse_reg_sz(pac_out) if pac_code == 0 else None
    auto_detect = _parse_reg_dword(ad_out) if ad_code == 0 else None

    return ProxyRegistrySnapshot(
        proxy_enable=proxy_enable,
        proxy_server=proxy_server,
        auto_config_url=auto_config_url,
        auto_detect=auto_detect,
    )

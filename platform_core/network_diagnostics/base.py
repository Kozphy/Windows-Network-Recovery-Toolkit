"""Shared types and helpers for OS-specific network diagnostics."""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

OsFamily = Literal["windows", "linux", "darwin", "unknown"]
LinuxDistro = Literal["ubuntu", "debian", "wsl", "unknown"]


def detect_os_family() -> OsFamily:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "darwin"
    return "unknown"


def is_wsl() -> bool:
    if detect_os_family() != "linux":
        return False
    try:
        release = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "microsoft" in release or "wsl" in release


def detect_linux_distro() -> LinuxDistro:
    if is_wsl():
        return "wsl"
    try:
        data = Path("/etc/os-release").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return "unknown"
    if "ubuntu" in data:
        return "ubuntu"
    if "debian" in data:
        return "debian"
    return "unknown"


def observation(signal_name: str, value: Any, *, source: str, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"signal_name": signal_name, "value": value, "source": source}
    row.update(extra)
    return row


def ping_host(host: str, *, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Best-effort reachability using system ping (read-only)."""
    family = detect_os_family()
    if family == "windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout_seconds * 1000)), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout_seconds))), host]
    if shutil.which(cmd[0]) is None:
        return {"host": host, "ok": False, "error": f"{cmd[0]} not on PATH"}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_seconds + 1,
            check=False,
        )
        ok = proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"host": host, "ok": False, "error": str(exc)}
    return {"host": host, "ok": ok, "returncode": proc.returncode}


def dns_observation(host: str = "www.microsoft.com") -> dict[str, Any]:
    try:
        addrs = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return observation(
            "dns_resolves",
            bool(addrs),
            source="socket.getaddrinfo",
            detail={"host": host, "address_count": len(addrs)},
        )
    except OSError as exc:
        return observation(
            "dns_resolves",
            False,
            source="socket.getaddrinfo",
            error=str(exc),
            limitations=["observation_only_not_proof"],
        )


class NetworkDiagnosticsProvider(ABC):
    """Read-only network observation contract (Observation != Proof)."""

    @abstractmethod
    def os_family(self) -> OsFamily: ...

    @abstractmethod
    def collect_observations(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def live_remediation_supported(self) -> bool: ...

    @abstractmethod
    def limitations(self) -> list[str]: ...

    def ping(self, host: str, *, timeout_seconds: float = 2.0) -> dict[str, Any]:
        return ping_host(host, timeout_seconds=timeout_seconds)

    def platform_payload(self) -> dict[str, Any]:
        return {
            "os_family": self.os_family(),
            "linux_distro": detect_linux_distro() if self.os_family() == "linux" else "unknown",
            "wsl": is_wsl(),
            "observations": self.collect_observations(),
            "live_remediation_supported": self.live_remediation_supported(),
            "limitations": self.limitations(),
            "epistemic_note": (
                "Observations are candidate signals only. "
                "Correlation != causation. Policy ALLOW != safety guarantee."
            ),
        }

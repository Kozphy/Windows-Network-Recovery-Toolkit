"""Linux / Debian / Ubuntu / WSL read-only network diagnostics."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any

from platform_core.network_diagnostics.base import (
    NetworkDiagnosticsProvider,
    detect_linux_distro,
    dns_observation,
    observation,
)


class LinuxNetworkDiagnostics(NetworkDiagnosticsProvider):
    """Observe-only diagnostics for Linux hosts and WSL."""

    def os_family(self) -> str:
        return "linux"

    def live_remediation_supported(self) -> bool:
        return False

    def limitations(self) -> list[str]:
        notes = [
            "Linux path is observe-only; registry/proxy remediation stays on Windows agents.",
            "Listener correlation is candidate evidence, not registry-writer proof.",
        ]
        if detect_linux_distro() == "wsl":
            notes.append("WSL shares Windows network stack for some paths; label observations separately.")
        return notes

    def collect_observations(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [
            observation("os_family", "linux", source="network_diagnostics.linux"),
            observation("linux_distro", detect_linux_distro(), source="network_diagnostics.linux"),
            observation("hostname", socket.gethostname(), source="network_diagnostics.linux"),
            dns_observation(),
        ]
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "no_proxy"):
            val = os.environ.get(key)
            if val:
                rows.append(
                    observation(f"env_{key.lower()}", val, source="network_diagnostics.linux")
                )
        try:
            route = Path("/proc/net/route").read_text(encoding="utf-8", errors="ignore")
            rows.append(
                observation(
                    "proc_net_route_present",
                    bool(route.strip()),
                    source="network_diagnostics.linux",
                )
            )
        except OSError:
            rows.append(
                observation(
                    "proc_net_route_present",
                    False,
                    source="network_diagnostics.linux",
                    limitations=["procfs_unavailable"],
                )
            )
        try:
            resolv = Path("/etc/resolv.conf").read_text(encoding="utf-8", errors="ignore")
            rows.append(
                observation(
                    "resolv_conf_present",
                    bool(resolv.strip()),
                    source="network_diagnostics.linux",
                )
            )
        except OSError:
            rows.append(
                observation(
                    "resolv_conf_present",
                    False,
                    source="network_diagnostics.linux",
                    limitations=["resolv_conf_unavailable"],
                )
            )
        return rows

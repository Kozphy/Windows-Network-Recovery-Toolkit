"""Name resolution evidence for localhost targets (read-only)."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResolutionEvidence:
    host: str
    ipv4: list[str] = field(default_factory=list)
    ipv6: list[str] = field(default_factory=list)
    has_127_0_0_1: bool = False
    has_ipv6_loopback: bool = False
    errors: list[str] = field(default_factory=list)
    hosts_file_mentions: list[str] = field(default_factory=list)
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "ipv4": list(self.ipv4),
            "ipv6": list(self.ipv6),
            "has_127_0_0_1": self.has_127_0_0_1,
            "has_ipv6_loopback": self.has_ipv6_loopback,
            "errors": list(self.errors),
            "hosts_file_mentions": list(self.hosts_file_mentions),
            "timestamp_utc": self.timestamp_utc,
        }


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_hosts_mentions(host: str) -> list[str]:
    """Best-effort hosts-file lines mentioning *host* (read-only; never edit)."""

    candidates = [
        Path(r"C:\Windows\System32\drivers\etc\hosts"),
        Path("/etc/hosts"),
    ]
    needle = host.lower()
    hits: list[str] = []
    for path in candidates:
        try:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if needle in stripped.lower():
                hits.append(stripped[:200])
                if len(hits) >= 5:
                    return hits
    return hits


def resolve_localhost_host(host: str, *, include_hosts_file: bool = True) -> ResolutionEvidence:
    """Resolve *host* to IPv4/IPv6 addresses via getaddrinfo (no mutation)."""

    errors: list[str] = []
    ipv4: list[str] = []
    ipv6: list[str] = []
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        errors.append(str(exc))
        infos = []
    except OSError as exc:
        errors.append(str(exc))
        infos = []

    for info in infos:
        family, _type, _proto, _canon, sockaddr = info
        addr = sockaddr[0]
        if family == socket.AF_INET and addr not in ipv4:
            ipv4.append(addr)
        elif family == socket.AF_INET6:
            # Strip zone id if present
            bare = addr.split("%", 1)[0]
            if bare not in ipv6:
                ipv6.append(bare)

    # Deterministic sort for audit stability
    ipv4 = sorted(ipv4)
    ipv6 = sorted(ipv6)

    hosts_hits = _safe_hosts_mentions(host) if include_hosts_file else []
    return ResolutionEvidence(
        host=host,
        ipv4=ipv4,
        ipv6=ipv6,
        has_127_0_0_1="127.0.0.1" in ipv4,
        has_ipv6_loopback="::1" in ipv6,
        errors=errors,
        hosts_file_mentions=hosts_hits,
        timestamp_utc=_now(),
    )


def loopback_probe_addresses(resolution: ResolutionEvidence) -> list[str]:
    """Addresses to TCP-probe: resolved loopbacks, with sensible defaults."""

    addrs: list[str] = []
    for a in resolution.ipv4:
        if a.startswith("127.") and a not in addrs:
            addrs.append(a)
    for a in resolution.ipv6:
        if a == "::1" and a not in addrs:
            addrs.append(a)
    if not addrs:
        # Still probe canonical loopbacks when resolution failed or returned empty
        addrs = ["127.0.0.1", "::1"]
    return addrs

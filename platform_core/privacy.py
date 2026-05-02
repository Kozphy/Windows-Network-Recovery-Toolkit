"""Privacy helpers — hash identifiers, mask IPs, redact paths (portfolio-safe defaults)."""

from __future__ import annotations

import hashlib
import re
from typing import Final

_PUBLIC_SUFFIX_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "google.com",
        "microsoft.com",
        "cloudflare.com",
        "example.com",
    },
)


def sanitize_hostname(value: str) -> str:
    """Replace hostname with a non-reversible short hash label for logs."""
    if not value or not value.strip():
        return "[empty]"
    digest = hashlib.sha256(value.strip().lower().encode()).hexdigest()[:16]
    return f"host_sha256_{digest}"


def sanitize_username(value: str) -> str:
    """Never persist raw Windows username."""
    if not value or not value.strip():
        return "[user]"
    return "user_redacted"


def sanitize_ip(value: str) -> str:
    """Mask private IPv4; pass through loopback; coarse-mask IPv6 private UC."""
    s = value.strip()
    if s in {"127.0.0.1", "::1"}:
        return s
    if re.match(r"^10\.\d+\.\d+\.\d+$", s):
        return "10.x.x.x"
    if re.match(r"^192\.168\.\d+\.\d+$", s):
        return "192.168.x.x"
    if re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$", s):
        return "172.16-31.x.x"
    if s.startswith("fe80:"):
        return "fe80::/link-local"
    return s


def sanitize_domain(value: str) -> str:
    """Allowlist a tiny set of public probe domains; otherwise redact."""
    v = value.strip().lower().rstrip(".")
    if v in _PUBLIC_SUFFIX_ALLOWLIST:
        return v
    if not v:
        return "[domain]"
    h = hashlib.sha256(v.encode()).hexdigest()[:12]
    return f"domain_sha256_{h}"


def stable_endpoint_hash(hostname: str, os_version: str, machine_hint: str | None = None) -> str:
    """Deterministic truncated SHA-256 for stable endpoint_id (no raw hostname stored)."""
    parts = [hostname, os_version, machine_hint or ""]
    raw = "|".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:32]


def redact_text(text: str) -> str:
    """Remove common user profile path segments and mask private IPs in free text."""
    s = text
    s = re.sub(
        r"(?i)C:\\\\Users\\\\[^\\]+",
        "C:\\\\Users\\\\[redacted]",
        s,
    )
    s = re.sub(
        r"(?i)(/users/)([^/\\s]+)(/)",
        r"\\1[redacted]\\3",
        s,
    )
    s = re.sub(r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "192.168.x.x", s)
    s = re.sub(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "10.x.x.x", s)
    return s

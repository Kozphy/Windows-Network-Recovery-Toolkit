"""Compare captured proxy snapshots — changed fields only, loopback anomaly hints."""

from __future__ import annotations

import re
from typing import Any

from .models import ProxySnapshot

_FIELDS = (
    "proxy_enable",
    "proxy_server",
    "proxy_override",
    "auto_config_url",
    "auto_detect",
    "winhttp_proxy",
    "winhttp_direct_access",
    "winhttp_proxy_server_literal",
    "git_http_proxy",
    "git_https_proxy",
    "npm_proxy",
    "npm_https_proxy",
    "user_http_proxy",
    "user_https_proxy",
    "user_all_proxy",
    "user_no_proxy",
)


def _loopback_hint(field: str, saved: Any, current: Any) -> str | None:
    blob = " ".join(str(x).lower() for x in (saved, current) if x is not None)
    if re.search(r"127\.0\.0\.1|localhost|::1\b", blob):
        return f"{field}_suspicious_loopback_proxy_candidate"
    return None


def diff_snapshots(saved: ProxySnapshot, current: ProxySnapshot) -> dict[str, Any]:
    """Return only fields that differ between ``saved`` baseline and ``current``."""

    changed: dict[str, Any] = {}
    hints: list[str] = []

    def add_change(key: str, a: Any, b: Any) -> None:
        changed[key] = {"saved": a, "current": b}
        h = _loopback_hint(key, a, b)
        if h:
            hints.append(h)

    for key in _FIELDS:
        a = getattr(saved, key)
        b = getattr(current, key)
        if key == "winhttp_proxy":
            sa = str(a or "").strip()
            sb = str(b or "").strip()
            if sa != sb:
                add_change(key, sa, sb)
            continue
        if a != b:
            add_change(key, a, b)

    return {"changed_fields": changed, "suspicious_loopback_hints": sorted(set(hints))}

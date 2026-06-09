"""DNS probe collector facade."""

from __future__ import annotations

from typing import Any


def collect_dns_signals(
    *,
    dns_ok: bool | None = None,
) -> dict[str, Any]:
    """Run lightweight DNS reachability probe (or accept injected result for tests)."""
    if dns_ok is None:
        from src.observability.dns_probe import nslookup_google_ok

        ok, _label = nslookup_google_ok()
    else:
        ok = dns_ok
    return {"dns_ok": ok, "probe": "nslookup google.com", "source": "dns_probe"}

"""DNS flush preview — informational only; no execution from this module."""

from __future__ import annotations

from typing import Any


def preview_dns_flush(*, dry_run: bool = True) -> dict[str, Any]:
    return {
        "action_id": "dns_flush",
        "dry_run": dry_run,
        "risk_level": "medium",
        "required_confirmation": "FLUSH_DNS_CACHE",
        "description": "Flush DNS resolver cache (ipconfig /flushdns). Preview only.",
        "argv_preview": ["ipconfig", "/flushdns"],
        "reversible": False,
    }

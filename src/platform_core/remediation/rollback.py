"""Rollback plan generation — required before any destructive preview."""

from __future__ import annotations

from typing import Any


def build_rollback_plan(
    *,
    action_id: str,
    prior_proxy_enable: int = 1,
    prior_proxy_server: str = "127.0.0.1:8080",
    dry_run: bool = True,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "dry_run": dry_run,
        "description": "Restore prior WinINET proxy registry values from captured snapshot.",
        "steps": [
            {
                "step": 1,
                "operation": "registry_restore",
                "target": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
                "values": {
                    "ProxyEnable": prior_proxy_enable,
                    "ProxyServer": prior_proxy_server,
                },
                "requires_typed_confirmation": True,
            },
            {
                "step": 2,
                "operation": "validate",
                "description": "Re-run proxy-proof and browser path probes after rollback.",
            },
        ],
        "limitations": [
            "Rollback restores captured values only; unknown prior PAC/override may differ.",
            "Rollback plan does not execute without explicit confirmation token.",
        ],
    }

"""WinINET proxy disable preview."""

from __future__ import annotations

from typing import Any


def preview_proxy_disable(*, dry_run: bool = True) -> dict[str, Any]:
    from src.proxy_guard.remediation import (
        build_user_proxy_disable_mutations,
        get_remediation_action,
    )

    action = get_remediation_action("disable_wininet_proxy")
    mutations, _warnings = build_user_proxy_disable_mutations(clear_proxy_server_value=True)
    mutation_preview = [
        {"argv": list(m.argv), "human": m.human}
        for m in mutations
    ]
    return {
        "action_id": action.action_id,
        "dry_run": dry_run,
        "risk_level": action.risk_level,
        "required_confirmation": action.required_confirmation,
        "mutations": mutation_preview,
        "reversible": action.reversible,
    }

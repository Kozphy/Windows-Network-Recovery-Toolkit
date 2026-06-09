"""Destructive action registry."""

from __future__ import annotations

from src.platform_core.contracts import DestructiveAction

DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset(a.value for a in DestructiveAction)

ACTION_ALIASES: dict[str, str] = {
    "disable_wininet_proxy": DestructiveAction.DISABLE_PROXY.value,
    "stop_proxy_listener": DestructiveAction.KILL_PROCESS.value,
    "stop_proxy_reverter": DestructiveAction.KILL_PROCESS.value,
    "registry_modification": DestructiveAction.REGISTRY_MODIFICATION.value,
    "reset_firewall": DestructiveAction.FIREWALL_RESET.value,
    "adapter_disable": DestructiveAction.ADAPTER_DISABLE.value,
}


def normalize_action(action: str) -> str:
    key = action.strip().lower().replace("-", "_")
    return ACTION_ALIASES.get(key, key)


def is_destructive(action: str) -> bool:
    norm = normalize_action(action)
    return norm in DESTRUCTIVE_ACTIONS or any(d in norm for d in ("disable", "kill", "reset", "delete"))

"""Safety constants and blocked-action registry."""

from __future__ import annotations

BLOCKED_ACTIONS = frozenset(
    {
        "KILL_PROXY_PROCESS",
        "FIREWALL_RESET",
        "ADAPTER_DISABLE",
        "WINHTTP_MODIFY",
    }
)

CONFIRMATION_TOKENS = {
    "DISABLE_WININET_PROXY": "DISABLE_WININET_PROXY",
}

DEFAULT_SAFETY_NOTES = [
    "Observation is not proof; correlation is not causation.",
    "Dry-run is default for all state-changing commands.",
    "No silent process kill, firewall reset, adapter disable, or WinHTTP modification.",
    "Policy permission is not a safety guarantee.",
]

POLICY_DISCLAIMER = (
    "This toolkit provides evidence-based endpoint diagnosis — not antivirus or EDR replacement."
)


def safety_checks_for(action: str) -> list[str]:
    checks = [
        "no_process_kill",
        "no_firewall_reset",
        "no_adapter_disable",
        "no_winhttp_modification_unless_explicit",
    ]
    if action in BLOCKED_ACTIONS:
        checks.append(f"blocked_action:{action}")
    return checks


def is_blocked_action(action: str) -> bool:
    return action.upper() in BLOCKED_ACTIONS

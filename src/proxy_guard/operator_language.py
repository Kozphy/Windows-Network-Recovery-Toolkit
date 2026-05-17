"""Operator-facing vocabulary for proxy guard policy outcomes (display layer only)."""

from __future__ import annotations

from typing import Any

# Internal JSONL / policy engine values remain ``allowed`` / ``blocked`` / ``observe``.
_OPERATOR_DECISION_MAP: dict[str, str] = {
    "allowed": "observe_no_rollback",
    "observe": "observe_no_rollback",
    "blocked": "rollback_eligible",
}

_OPERATOR_DECISION_NOTES: dict[str, str] = {
    "observe_no_rollback": (
        "Guard is not auto-rolling back this change. This does NOT mean the proxy state is safe."
    ),
    "rollback_eligible": "Change matched a blocked policy path; rollback may be available with confirmation.",
}


def display_policy_decision(raw: Any) -> str:
    """Map stored policy ``decision`` to operator-safe wording."""

    key = str(raw or "").strip().lower()
    return _OPERATOR_DECISION_MAP.get(key, key or "unknown")


def policy_decision_note(display_decision: str) -> str:
    """Short disclaimer for operator reports."""

    return _OPERATOR_DECISION_NOTES.get(
        display_decision,
        "See policy reason; internal decision codes may differ from operator labels.",
    )

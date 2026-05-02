"""Allowlist/blocklist policy for network-state drift (pure evaluation)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..proxy_guard.parser import ParsedProxy


def _host_guess(parsed: ParsedProxy) -> str | None:
    h = parsed.localhost_host or (parsed.raw or "").strip()
    return h.lower() if h else None


@dataclass(frozen=True)
class NetworkStatePolicy:
    """Loaded from ``config/network_state_policy.json``."""

    allowed_process_names: tuple[str, ...]
    blocked_process_names: tuple[str, ...]
    allowed_proxy_hosts: tuple[str, ...]
    blocked_proxy_hosts: tuple[str, ...]
    rollback_on_unknown_loopback: bool
    alert_on_unknown_loopback: bool

    @classmethod
    def default(cls) -> NetworkStatePolicy:
        return cls((), (), (), (), False, True)

    @classmethod
    def from_file(cls, path: Path) -> NetworkStatePolicy:
        if not path.is_file():
            return cls.default()
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls.default()
        if not isinstance(blob, dict):
            return cls.default()

        def tup(key: str) -> tuple[str, ...]:
            v = blob.get(key)
            if isinstance(v, list):
                return tuple(str(x).lower() for x in v)
            return ()

        return cls(
            allowed_process_names=tup("allowed_process_names"),
            blocked_process_names=tup("blocked_process_names"),
            allowed_proxy_hosts=tuple(str(x).lower() for x in blob.get("allowed_proxy_hosts", []) if isinstance(x, str)),
            blocked_proxy_hosts=tuple(str(x).lower() for x in blob.get("blocked_proxy_hosts", []) if isinstance(x, str)),
            rollback_on_unknown_loopback=bool(blob.get("rollback_on_unknown_loopback", False)),
            alert_on_unknown_loopback=bool(blob.get("alert_on_unknown_loopback", True)),
        )


def evaluate_network_state_policy(
    policy: NetworkStatePolicy,
    *,
    parsed: ParsedProxy,
    suspicions: list[str],
    attribution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return advisory decision consumed by CLI/report (no subprocess side effects)."""

    reasons: list[str] = []
    decision = "observe"
    host_s = (_host_guess(parsed) or "") or ""

    for blocked in policy.blocked_proxy_hosts:
        if blocked and blocked in host_s:
            reasons.append(f"blocked_proxy_host:{blocked}")
            decision = "blocked"

    if decision != "blocked" and policy.blocked_proxy_hosts and parsed.raw:
        raw_l = parsed.raw.lower()
        for blocked in policy.blocked_proxy_hosts:
            if blocked in raw_l:
                reasons.append(f"blocked_literal:{blocked}")
                decision = "blocked"

    lowered_allowed_host = False
    for allowed in policy.allowed_proxy_hosts:
        if allowed and allowed in host_s:
            lowered_allowed_host = True
            break
        if allowed and parsed.raw and allowed in parsed.raw.lower():
            lowered_allowed_host = True
            break

    actor_names = []
    if attribution:
        owners = attribution.get("owners") or []
        if isinstance(owners, list):
            for o in owners:
                if isinstance(o, dict) and o.get("process_name"):
                    actor_names.append(str(o["process_name"]).lower())

    for blocked_name in policy.blocked_process_names:
        if blocked_name and any(blocked_name in n for n in actor_names):
            reasons.append(f"blocked_process_heuristic:{blocked_name}")
            if decision != "blocked":
                decision = "blocked"

    for allowed_name in policy.allowed_process_names:
        if allowed_name and any(allowed_name in n for n in actor_names):
            reasons.append(f"allowed_process_heuristic:{allowed_name}")
            if decision == "observe":
                decision = "allowed_context"

    loopback_unknown = any("loopback" in s for s in suspicions) or (
        parsed.is_localhost_proxy and not lowered_allowed_host
    )
    if loopback_unknown and policy.alert_on_unknown_loopback:
        reasons.append("alert_unknown_loopback_context")
    if loopback_unknown and policy.rollback_on_unknown_loopback and decision not in ("blocked",):
        reasons.append("rollback_suggested_unknown_loopback")
        decision = "rollback_suggested"

    return {"decision": decision, "reasons": sorted(set(reasons))}

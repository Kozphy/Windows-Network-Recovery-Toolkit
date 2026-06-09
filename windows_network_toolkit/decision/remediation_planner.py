"""Remediation planning from decision + policy."""

from __future__ import annotations

from typing import Any

from windows_network_toolkit.remediation import (
    preview_dns_flush,
    preview_proxy_disable,
    preview_rollback,
    preview_stop_listener,
    preview_stop_reverter,
)

from .decision_model import DecisionResult, IncidentType


def plan_remediation(decision: DecisionResult, *, dry_run: bool = True) -> dict[str, Any]:
    previews: list[dict[str, Any]] = []
    blocked = list(decision.blocked_actions)
    allowed = list(decision.allowed_actions)

    if decision.incident_type in {
        IncidentType.WININET_PROXY_DRIFT,
        IncidentType.PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS,
    }:
        previews.append(preview_proxy_disable(dry_run=dry_run))
        allowed.append("disable_wininet_proxy")

    if decision.incident_type == IncidentType.WRITER_AND_LISTENER_MATCH:
        previews.append(preview_stop_listener(dry_run=dry_run))
        previews.append(preview_stop_reverter(dry_run=dry_run))

    if decision.incident_type == IncidentType.DNS_OK_BROWSER_FAIL:
        previews.append(preview_dns_flush(dry_run=dry_run))

    rollback = preview_rollback(dry_run=dry_run)

    return {
        "dry_run": dry_run,
        "previews": previews,
        "rollback_plan": rollback,
        "allowed_actions": sorted(set(allowed)),
        "blocked_actions": sorted(set(blocked)),
    }

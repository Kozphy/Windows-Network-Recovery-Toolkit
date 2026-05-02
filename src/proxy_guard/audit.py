"""Append structured :class:`~src.proxy_guard.models.ProxyGuardAuditRecord` JSONL rows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.jsonl import append_jsonl
from .models import ProxyGuardAuditRecord, RollbackPlan


def pipeline_audit_path(repo_root: Path) -> Path:
    """Secondary sink for unified v1 pipeline JSON (does not replace schema v2 rows)."""

    return repo_root / "logs" / "proxy_guard_pipeline_audit.jsonl"


def emit_pipeline_audit_v1(repo_root: Path, payload: dict[str, Any]) -> None:
    """Append ``schema_version`` 1 unified detect→attribute→decide→rollback audit lines."""

    path = pipeline_audit_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(path, payload)


def default_audit_paths(repo_root: Path) -> dict[str, Path]:
    """Return canonical watch/actions/audit sink paths under *repo_root*."""
    return {
        "watch": repo_root / "reports" / "proxy_guard_watch.jsonl",
        "actions": repo_root / "reports" / "proxy_guard_actions.jsonl",
        "audit": repo_root / "logs" / "proxy_guard_audit.jsonl",
    }


def emit_proxy_guard_audit(record: ProxyGuardAuditRecord, *, repo_root: Path) -> None:
    """Write the same JSON object to watch/actions/audit sinks (idempotent append)."""
    paths = default_audit_paths(repo_root)
    for key in ("watch", "actions", "audit"):
        path = paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(path, record.to_jsonable())


def build_rollback_plan(
    *,
    decision: str,
    rollback_allowed: bool,
    lkg_present: bool,
    auto_rollback_enabled: bool,
    live_rollback_enabled: bool,
    explicit_winhttp_data: bool,
    restore_git_npm_env: bool,
) -> RollbackPlan:
    """``lkg_present`` historically meant LKG file on disk; callers may pass True when any prior snapshot exists."""

    wants = decision == "blocked" and rollback_allowed and auto_rollback_enabled and lkg_present
    return RollbackPlan(
        dry_run_requested=not live_rollback_enabled,
        restore_wininet=wants,
        restore_winhttp=wants and explicit_winhttp_data,
        would_restore_git_or_env=restore_git_npm_env,
        rationale=(
            "lkg_snapshot_restores_config_instead_of_blind_disable",
            "git_npm_env_requires_explicit_operator_flag",
        ),
    )

"""Deterministic OpenClaw task policy — rejects high-risk and prohibited work."""

from __future__ import annotations

import re
from typing import Any

from src.platform_core.openclaw.models import (
    DEFAULT_BRANCHES,
    DEFAULT_FORBIDDEN_PATHS,
    FORBIDDEN_ACTION_KEYWORDS,
    SUPPORTED_AUTO_RISKS,
    OpenClawTask,
    PolicyResult,
)

_BRANCH_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_slug(text: str, *, max_len: int = 48) -> str:
    """Sanitize user/task text for branch names — no shell metacharacters."""
    cleaned = _BRANCH_SLUG_RE.sub("-", (text or "").strip().lower()).strip("-._")
    return (cleaned or "task")[:max_len]


def sanitize_task_id(task_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "", (task_id or "").strip())
    if not cleaned:
        raise ValueError("task_id must contain alphanumeric characters")
    return cleaned[:64]


def expected_branch_name(task: OpenClawTask) -> str:
    tid = sanitize_task_id(task.task_id)
    slug = sanitize_slug(task.title)
    return f"agent/openclaw/{tid}-{slug}"


def _normalize_path(path: str) -> str:
    """Normalize path separators without stripping leading dots from names like ``.env``."""
    norm = path.replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def _path_is_forbidden(path: str, extra: tuple[str, ...]) -> bool:
    norm = _normalize_path(path)
    banned = set(DEFAULT_FORBIDDEN_PATHS) | {_normalize_path(p) for p in extra}
    for item in banned:
        if not item:
            continue
        if norm == item or norm.startswith(item.rstrip("/") + "/") or item.rstrip("/") == norm:
            return True
        # Exact file match for .env style
        if norm.endswith(item) and item.startswith(".env"):
            return True
    return False


def _text_requests_forbidden_action(blob: str) -> str | None:
    lowered = blob.lower()
    for kw in FORBIDDEN_ACTION_KEYWORDS:
        if kw in lowered:
            return kw
    return None


def evaluate_task_policy(
    task: OpenClawTask,
    *,
    default_branch: str = "Multi_Domain_Decision_Platform",
) -> PolicyResult:
    """Return ALLOW only for explicitly approved low/medium coding tasks."""
    reasons: list[str] = []

    if not task.task_id:
        reasons.append("missing_task_id")
    if not task.title:
        reasons.append("missing_title")
    if not task.description.strip():
        reasons.append("empty_acceptance_criteria")
    if task.approved is not True:
        reasons.append("not_approved")

    if task.risk_level not in SUPPORTED_AUTO_RISKS:
        if task.risk_level in {"high", "critical"}:
            reasons.append("risk_requires_manual_execution")
        else:
            reasons.append("unsupported_risk_level")

    branch = task.requested_branch or ""
    if branch:
        base = branch.split("/")[-1] if branch.count("/") == 0 else branch
        if branch in DEFAULT_BRANCHES or base in DEFAULT_BRANCHES:
            reasons.append("default_branch_forbidden")
        if branch.lower() == default_branch.lower():
            reasons.append("default_branch_forbidden")
        if not branch.startswith("agent/openclaw/"):
            reasons.append("branch_must_use_agent_openclaw_prefix")

    for path in task.allowed_paths:
        if _path_is_forbidden(path, task.forbidden_paths):
            reasons.append(f"forbidden_path_requested:{_normalize_path(path)}")

    for path in task.forbidden_paths:
        # Task may list forbidden paths as deny-list — that is fine.
        # Only block if they also appear in allowed_paths (handled above).
        _ = path

    # Always treat default forbidden set as blocked if mentioned in description as targets
    hit = _text_requests_forbidden_action(f"{task.title}\n{task.description}")
    if hit:
        reasons.append(f"forbidden_action:{hit}")

    # Require agent-ready label when labels are present (GitHub issue path)
    if task.labels and "agent-ready" not in {x.lower() for x in task.labels}:
        reasons.append("missing_agent_ready_label")

    if reasons:
        return PolicyResult(decision="BLOCK", reasons=tuple(dict.fromkeys(reasons)))
    return PolicyResult(decision="ALLOW", reasons=("approved_low_or_medium_task",))


def validate_changed_paths(
    changed_files: list[str],
    task: OpenClawTask,
    *,
    max_files: int = 20,
    max_changed_lines: int | None = None,
    changed_line_count: int | None = None,
) -> PolicyResult:
    """Block if the working tree touches prohibited paths or exceeds size limits."""
    reasons: list[str] = []
    if len(changed_files) > max_files:
        reasons.append(f"too_many_files:{len(changed_files)}>{max_files}")
    if max_changed_lines is not None and changed_line_count is not None:
        if changed_line_count > max_changed_lines:
            reasons.append(f"too_many_lines:{changed_line_count}>{max_changed_lines}")

    allowed_prefixes = [_normalize_path(p) for p in task.allowed_paths if p]
    for path in changed_files:
        norm = _normalize_path(path)
        if _path_is_forbidden(norm, task.forbidden_paths):
            reasons.append(f"prohibited_file_modified:{norm}")
            continue
        if allowed_prefixes:
            if not any(
                norm == p.rstrip("/") or norm.startswith(p.rstrip("/") + "/") or norm.startswith(p)
                for p in allowed_prefixes
            ):
                reasons.append(f"path_outside_allowlist:{norm}")

    if reasons:
        return PolicyResult(decision="BLOCK", reasons=tuple(dict.fromkeys(reasons)))
    return PolicyResult(decision="ALLOW", reasons=("changed_paths_within_policy",))


def task_from_mapping(raw: dict[str, Any]) -> OpenClawTask:
    return OpenClawTask.from_dict(raw)

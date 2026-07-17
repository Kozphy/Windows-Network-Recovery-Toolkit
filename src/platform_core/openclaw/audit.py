"""Structured audit record for OpenClaw coding runs (no secrets)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = "openclaw_coding_run.v1"

RunStatus = Literal[
    "policy_blocked",
    "validation_failed",
    "draft_pr_created",
    "completed_local",
    "error",
]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class OpenClawRunAudit:
    task_id: str
    branch: str
    started_at: str
    completed_at: str | None = None
    status: RunStatus = "completed_local"
    changed_files: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    policy_decision: str = "ALLOW"
    limitations: list[str] = field(default_factory=list)
    pull_request_url: str | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def finish(self, status: RunStatus) -> None:
        self.status = status
        self.completed_at = _now()


def new_run_audit(*, task_id: str, branch: str, policy_decision: str) -> OpenClawRunAudit:
    return OpenClawRunAudit(
        task_id=task_id,
        branch=branch,
        started_at=_now(),
        policy_decision=policy_decision,
        limitations=[
            "OpenClaw generates candidate changes only.",
            "Passing tests does not prove the code is free of defects or safe for production.",
            "Draft PRs must not be merged without human review and required CI checks.",
        ],
    )


def write_run_audit(audit: OpenClawRunAudit, directory: Path) -> Path:
    """Write audit JSON under a local runtime directory (gitignored)."""
    directory.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in audit.task_id)[:64]
    path = directory / f"openclaw_run_{safe_id}_{audit.started_at.replace(':', '')}.json"
    path.write_text(json.dumps(audit.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path

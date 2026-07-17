"""OpenClaw coding-agent policy models — approved tasks only; no live remediation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RiskLevel = Literal["low", "medium", "high", "critical"]
PolicyDecision = Literal["ALLOW", "BLOCK"]

DEFAULT_BRANCHES = frozenset(
    {
        "main",
        "master",
        "Multi_Domain_Decision_Platform",
        "multi_domain_decision_platform",
    }
)

DEFAULT_FORBIDDEN_PATHS = frozenset(
    {
        ".env",
        ".env.local",
        "platform_data/",
        ".audit/",
        ".github/workflows/deploy.yml",
        ".github/workflows/build.yml",
    }
)

FORBIDDEN_ACTION_KEYWORDS = frozenset(
    {
        "deploy",
        "merge pull request",
        "merge pr",
        "auto-merge",
        "automerge",
        "access .env",
        "read secrets",
        "ssh key",
        "api token",
        "registry mutation",
        "disable_wininet",
        "live registry",
        "firewall reset",
        "reset firewall",
        "adapter disable",
        "disable adapter",
        "process kill",
        "kill process",
        "taskkill",
        "credential",
        "private key",
    }
)

SUPPORTED_AUTO_RISKS = frozenset({"low", "medium"})


@dataclass(frozen=True)
class OpenClawTask:
    """Approved coding task for the automated runner."""

    task_id: str
    title: str
    description: str
    approved: bool
    risk_level: str
    allowed_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    requested_branch: str = ""
    labels: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> OpenClawTask:
        allowed = raw.get("allowed_paths") or []
        forbidden = raw.get("forbidden_paths") or []
        labels = raw.get("labels") or []
        return cls(
            task_id=str(raw.get("task_id") or "").strip(),
            title=str(raw.get("title") or "").strip(),
            description=str(raw.get("description") or "").strip(),
            approved=bool(raw.get("approved") is True),
            risk_level=str(raw.get("risk_level") or "").strip().lower(),
            allowed_paths=tuple(str(p) for p in allowed),
            forbidden_paths=tuple(str(p) for p in forbidden),
            requested_branch=str(raw.get("requested_branch") or raw.get("branch") or "").strip(),
            labels=tuple(str(x) for x in labels),
        )


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reasons: tuple[str, ...] = ()
    limitations: tuple[str, ...] = field(
        default_factory=lambda: (
            "Policy permission is not a safety guarantee.",
            "Passing tests does not prove production readiness.",
            "Draft PRs require human review before merge.",
        )
    )

    @property
    def allowed(self) -> bool:
        return self.decision == "ALLOW"

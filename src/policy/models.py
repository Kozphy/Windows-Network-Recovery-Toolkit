"""Policy engine models — Step 3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.classification.models import ProcessClassificationResult


class PolicyDecisionKind(str, Enum):
    ALLOW = "ALLOW"
    OBSERVE = "OBSERVE"
    ALERT = "ALERT"
    PREVIEW_DISABLE = "PREVIEW_DISABLE"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    BLOCK_RECOMMENDED = "BLOCK_RECOMMENDED"
    ESCALATE_REVIEW = "ESCALATE_REVIEW"
    CORRELATION_ONLY_ALERT = "CORRELATION_ONLY_ALERT"


class PolicySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ProxyPolicyUserConfig:
    allow_known_cursor: bool = True
    cursor_action: str = "OBSERVE"
    vscode_action: str = "OBSERVE"
    dev_proxy_action: str = "OBSERVE"
    active_dev_session: bool = True
    deny_unknown_localhost: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProxyPolicyUserConfig:
        return cls(
            allow_known_cursor=bool(raw.get("allow_known_cursor", True)),
            cursor_action=str(raw.get("cursor_proxy_action", raw.get("cursor_action", "OBSERVE"))),
            vscode_action=str(raw.get("vscode_extension_action", raw.get("vscode_action", "OBSERVE"))),
            dev_proxy_action=str(raw.get("known_dev_proxy_action", raw.get("dev_proxy_action", "OBSERVE"))),
            active_dev_session=bool(raw.get("active_dev_session", True)),
            deny_unknown_localhost=bool(raw.get("deny_unknown_localhost_proxy", raw.get("deny_unknown_localhost", True))),
        )


@dataclass
class ProxyPolicyInput:
    causation_level: str
    classification_result: ProcessClassificationResult | dict[str, Any]
    proxy_before: dict[str, Any]
    proxy_after: dict[str, Any]
    registry_writer: str | None = None
    registry_target: str | None = None
    registry_details: str | None = None
    localhost_port: int | None = None
    user_config: ProxyPolicyUserConfig | None = None
    timestamp_utc: str = ""
    changed_fields: list[str] = field(default_factory=list)
    risk_level: str | None = None


@dataclass
class ProxyPolicyDecision:
    decision: PolicyDecisionKind
    severity: PolicySeverity
    allowed_actions: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    reason: str = ""
    explanation: list[str] = field(default_factory=list)
    next_safe_steps: list[str] = field(default_factory=list)

    @property
    def action(self) -> str:
        return self.decision.value

    @property
    def confidence(self) -> float:
        return {"LOW": 0.5, "MEDIUM": 0.65, "HIGH": 0.82, "CRITICAL": 0.92}.get(self.severity.value, 0.6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "action": self.decision.value,
            "severity": self.severity.value,
            "allowed_actions": list(self.allowed_actions),
            "blocked_actions": list(self.blocked_actions),
            "requires_confirmation": self.requires_confirmation,
            "reason": self.reason,
            "explanation": list(self.explanation),
            "next_safe_steps": list(self.next_safe_steps),
            "confidence": self.confidence,
            "requires_human_review": self.requires_confirmation,
        }

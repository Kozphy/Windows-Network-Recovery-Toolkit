"""Unified WNT data models — JSON-serializable at CLI boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProxyState:
    timestamp_utc: str
    wininet_proxy_enabled: bool
    wininet_proxy_server: str
    wininet_proxy_override: str
    wininet_auto_config_url: str
    winhttp_direct_access: bool
    winhttp_raw_excerpt: str
    localhost_port: int | None
    source: str = "wininet_registry+netsh_winhttp"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "wininet_proxy_enabled": self.wininet_proxy_enabled,
            "wininet_proxy_server": self.wininet_proxy_server,
            "wininet_proxy_override": self.wininet_proxy_override,
            "wininet_auto_config_url": self.wininet_auto_config_url,
            "winhttp_direct_access": self.winhttp_direct_access,
            "winhttp_raw_excerpt": self.winhttp_raw_excerpt,
            "localhost_port": self.localhost_port,
            "source": self.source,
            "errors": self.errors,
        }


@dataclass
class ProcessOwner:
    listener_found: bool
    pid: int | None = None
    name: str = ""
    exe_path: str = ""
    cmdline: str = ""
    username: str = ""
    signed_status: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if not self.listener_found:
            return {
                "listener_found": False,
                "pid": self.pid,
                "name": self.name,
                "exe_path": self.exe_path,
                "cmdline": self.cmdline,
                "username": self.username,
                "signed_status": self.signed_status,
                "errors": self.errors,
            }
        return {
            "listener_found": True,
            "pid": self.pid,
            "name": self.name,
            "exe_path": self.exe_path,
            "cmdline": self.cmdline,
            "username": self.username,
            "signed_status": self.signed_status,
            "errors": self.errors,
        }


@dataclass
class ClassificationResult:
    primary_classification: str
    secondary_signals: list[str]
    severity: str
    confidence: float
    reasoning: str
    evidence: list[str]
    recommended_next_actions: list[str]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_classification": self.primary_classification,
            "secondary_signals": self.secondary_signals,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "recommended_next_actions": self.recommended_next_actions,
            "limitations": self.limitations,
        }


@dataclass
class ProofAttempt:
    name: str
    status: str
    meaning: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "meaning": self.meaning}


@dataclass
class ProofResult:
    observation: dict[str, Any]
    hypothesis: str
    proof_attempts: list[ProofAttempt]
    conclusion_status: str
    confidence: float
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation": self.observation,
            "hypothesis": self.hypothesis,
            "proof_attempts": [p.to_dict() for p in self.proof_attempts],
            "conclusion": {"status": self.conclusion_status, "confidence": round(self.confidence, 3)},
            "limitations": self.limitations,
        }


@dataclass
class AuditEvent:
    timestamp_utc: str
    command: str
    observation: dict[str, Any]
    hypothesis: str
    action_requested: str
    action_allowed: bool
    action_taken: str
    confirmation_used: str
    result: dict[str, Any]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "command": self.command,
            "observation": self.observation,
            "hypothesis": self.hypothesis,
            "action_requested": self.action_requested,
            "action_allowed": self.action_allowed,
            "action_taken": self.action_taken,
            "confirmation_used": self.confirmation_used,
            "result": self.result,
            "limitations": self.limitations,
        }


@dataclass
class PolicyDecision:
    action: str
    allowed: bool
    requires_confirmation: bool
    confirmation_token: str
    risk_level: str
    rationale: str
    safety_checks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_token": self.confirmation_token,
            "risk_level": self.risk_level,
            "rationale": self.rationale,
            "safety_checks": self.safety_checks,
        }

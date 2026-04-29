"""Structured types for evidence, classification, repair planning, and verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Ordered list used by classifier output and planner routing.
RootCauseCategory = Literal[
    "dns_issue",
    "proxy_issue",
    "tcp_issue",
    "https_issue",
    "tls_cert_issue",
    "winsock_issue",
    "firewall_issue",
    "connection_exhaustion",
    "unknown",
]

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class DiagnosticEvidence:
    """Structured snapshot from collector or JSON fixtures (no credentials)."""

    ping_ok: bool
    dns_ok: bool
    tcp_443_ok: bool
    https_ok: bool
    winhttp_proxy_summary: str
    user_proxy_enabled: bool
    user_proxy_server: str | None
    tls_cert_issue_detected: bool
    firewall_blocking_suspected: bool
    time_wait_count: int
    established_count: int
    recent_processes: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ping_ok": self.ping_ok,
            "dns_ok": self.dns_ok,
            "tcp_443_ok": self.tcp_443_ok,
            "https_ok": self.https_ok,
            "winhttp_proxy_summary": self.winhttp_proxy_summary,
            "user_proxy_enabled": self.user_proxy_enabled,
            "user_proxy_server": self.user_proxy_server,
            "tls_cert_issue_detected": self.tls_cert_issue_detected,
            "firewall_blocking_suspected": self.firewall_blocking_suspected,
            "time_wait_count": self.time_wait_count,
            "established_count": self.established_count,
            "recent_processes": list(self.recent_processes),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiagnosticEvidence:
        return cls(
            ping_ok=bool(data["ping_ok"]),
            dns_ok=bool(data["dns_ok"]),
            tcp_443_ok=bool(data["tcp_443_ok"]),
            https_ok=bool(data["https_ok"]),
            winhttp_proxy_summary=str(data.get("winhttp_proxy_summary", "")),
            user_proxy_enabled=bool(data.get("user_proxy_enabled", False)),
            user_proxy_server=data.get("user_proxy_server"),
            tls_cert_issue_detected=bool(data.get("tls_cert_issue_detected", False)),
            firewall_blocking_suspected=bool(data.get("firewall_blocking_suspected", False)),
            time_wait_count=int(data.get("time_wait_count", 0)),
            established_count=int(data.get("established_count", 0)),
            recent_processes=list(data.get("recent_processes") or []),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True)
class RankedCause:
    category: RootCauseCategory
    confidence: float  # 0.0–1.0
    explanation: str


@dataclass(frozen=True)
class RepairStep:
    """Single remediation step referencing a repo script (never credentials)."""

    script_relative_path: str
    description: str
    risk: RiskLevel
    requires_confirmation: bool
    destructive: bool


@dataclass(frozen=True)
class RepairPlan:
    steps: tuple[RepairStep, ...]
    rationale: str
    verification_hint: str


@dataclass(frozen=True)
class VerificationResult:
    """Outcome after re-running checks post-repair."""

    passed: bool
    summary: str
    evidence_after: DiagnosticEvidence
    compared_fields: dict[str, tuple[Any, Any]]

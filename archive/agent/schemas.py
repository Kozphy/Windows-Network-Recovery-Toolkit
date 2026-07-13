"""Typed data contracts for local diagnostic workflows.

This module defines immutable schema objects shared across collector,
classifier, planner, executor, and verifier modules in the local agent flow.

Key invariants:
    - Schema objects are JSON-serializable via explicit conversion helpers.
    - Categories and risk levels are constrained through Literal types.
    - Evidence payloads avoid credential/secret capture by design.
"""

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
    """Normalized diagnostic snapshot from live probes or fixtures.

    Attributes:
        ping_ok: ICMP reachability signal for known public endpoint.
        dns_ok: DNS resolution signal from resolver probe.
        tcp_443_ok: TCP connectivity signal for HTTPS port.
        https_ok: HTTPS probe success indicator.
        winhttp_proxy_summary: Raw WinHTTP proxy summary text.
        user_proxy_enabled: Whether user-level proxy appears configured.
        user_proxy_server: Optional user proxy server value when detected.
        tls_cert_issue_detected: Heuristic TLS/certificate issue flag.
        firewall_blocking_suspected: Conservative firewall-path suspicion flag.
        time_wait_count: Current TIME_WAIT socket count.
        established_count: Current ESTABLISHED socket count.
        recent_processes: Recent process names for correlation context.
        notes: Additional collector hints or caveats.
    """

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
        """Serialize evidence into primitive JSON-compatible mapping.

        Returns:
            dict[str, Any]: Dictionary representation preserving all fields.
        """
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
        """Construct evidence from loosely typed mapping data.

        Schema assumptions:
            - Missing optional fields fall back to conservative defaults.
            - Required booleans are coercible via `bool(...)`.

        Args:
            data: Source mapping from fixture or deserialized payload.

        Returns:
            DiagnosticEvidence: Normalized dataclass instance.

        Raises:
            KeyError: If required baseline keys are absent.
            ValueError: If numeric fields cannot be coerced to integers.
            TypeError: If field values are of unsupported types.
        """
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
    """One ranked root-cause hypothesis emitted by classifier.

    Attributes:
        category: Canonical cause category.
        confidence: Confidence score in the range [0.0, 1.0].
        explanation: Human-readable rationale for ranking.
    """

    category: RootCauseCategory
    confidence: float  # 0.0–1.0
    explanation: str


@dataclass(frozen=True)
class RepairStep:
    """One remediation step referencing a repository script.

    Attributes:
        script_relative_path: Path to script under repository root.
        description: User-facing explanation of intended remediation.
        risk: Risk label used for gating and UI communication.
        requires_confirmation: Whether explicit user approval is mandatory.
        destructive: Whether step may mutate network state significantly.
    """

    script_relative_path: str
    description: str
    risk: RiskLevel
    requires_confirmation: bool
    destructive: bool


@dataclass(frozen=True)
class RepairPlan:
    """Ordered repair plan associated with a selected hypothesis.

    Attributes:
        steps: Ordered remediation steps to evaluate/execute.
        rationale: Why this plan matches current diagnosis.
        verification_hint: Post-repair checks recommended to operator.
    """

    steps: tuple[RepairStep, ...]
    rationale: str
    verification_hint: str


@dataclass(frozen=True)
class VerificationResult:
    """Post-repair verification outcome with before/after comparison.

    Attributes:
        passed: Whether verification met pass criteria.
        summary: Compact verification summary string.
        evidence_after: Re-collected evidence after repair attempt.
        compared_fields: Map of key signal names to `(before, after)` tuples.
    """

    passed: bool
    summary: str
    evidence_after: DiagnosticEvidence
    compared_fields: dict[str, tuple[Any, Any]]

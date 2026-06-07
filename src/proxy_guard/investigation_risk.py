"""Proxy risk classification for read-only investigation bundles.

High risk does not imply malware. Categories describe unexpected or sticky local proxy behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RiskCategory = Literal[
    "NO_PROXY",
    "MANUAL_LOCALHOST_PROXY",
    "KNOWN_DEV_PROXY",
    "KNOWN_SECURITY_TOOL",
    "UNKNOWN_LOCAL_PROXY",
    "SUSPICIOUS_LOCAL_PROXY",
    "POSSIBLE_MITM_RISK",
    "HIGH_RISK_PROXY_TRANSITION",
    "REMEDIATION_NOT_STICKY",
]
PolicyAction = Literal[
    "OBSERVE_ONLY",
    "EXPORT_EVIDENCE",
    "DISABLE_WININET_PROXY",
    "TERMINATE_PROXY_LISTENER",
    "TERMINATE_PROXY_REVERTER",
    "NO_ACTION",
]

_DEV_PROCESS_NAMES = frozenset({"node.exe", "python.exe", "electron.exe", "npm.cmd", "pnpm.exe"})
_DEV_PARENT_NAMES = frozenset({"powershell.exe", "pwsh.exe", "cmd.exe", "cursor.exe", "code.exe"})
_SECURITY_TOOL_NAMES = frozenset({"fiddler.exe", "charles.exe", "mitmproxy.exe", "proxifier.exe"})
_PROXY_CMDLINE_TERMS = (
    "proxy",
    "tunnel",
    "socks",
    "http-proxy",
    "mitm",
    "mcp",
    "dev server",
    "dev-server",
)
_USER_WRITABLE_MARKERS = ("\\appdata\\", "\\temp\\", "\\users\\", "\\downloads\\")


@dataclass(frozen=True)
class InvestigationRisk:
    """Risk classification with policy recommendation (preview only)."""

    category: RiskCategory
    risk_level: RiskLevel
    confidence: float
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    recommended_policy_action: PolicyAction
    recommended_next_step: str

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "limitations": list(self.limitations),
            "recommended_policy_action": self.recommended_policy_action,
            "recommended_next_step": self.recommended_next_step,
        }


def _norm_name(name: str | None) -> str:
    return (name or "").strip().lower()


def _path_user_writable(path: str | None) -> bool:
    if not path or not path.strip():
        return False
    norm = path.strip().strip('"').lower().replace("/", "\\")
    return any(marker in norm for marker in _USER_WRITABLE_MARKERS)


def _cmdline_has_proxy_terms(cmdline: str | None) -> bool:
    if not cmdline:
        return False
    low = cmdline.lower()
    return any(term in low for term in _PROXY_CMDLINE_TERMS)


def classify_investigation_risk(
    *,
    proxy_enable: int | None,
    parsed: dict[str, Any],
    port_owner: dict[str, Any] | None,
    before_snapshot: dict[str, Any] | None,
    registry_writer_proof: bool = False,
) -> InvestigationRisk:
    """Classify localhost proxy posture using observable signals only."""

    limitations = (
        "High risk does not mean malware.",
        "Listener correlation is not registry writer proof.",
    )
    enabled = proxy_enable == 1
    is_localhost = bool(parsed.get("is_localhost_proxy"))
    port = parsed.get("localhost_port")

    if not enabled:
        return InvestigationRisk(
            category="NO_PROXY",
            risk_level="LOW",
            confidence=0.95,
            evidence=("WinINET ProxyEnable is off.",),
            limitations=limitations,
            recommended_policy_action="OBSERVE_ONLY",
            recommended_next_step="No WinINET remediation required; monitor with proxy-watch if drift recurs.",
        )

    if enabled and not is_localhost and not parsed.get("proxy_server"):
        return InvestigationRisk(
            category="NO_PROXY",
            risk_level="LOW",
            confidence=0.7,
            evidence=("ProxyEnable is on but ProxyServer is empty or non-localhost.",),
            limitations=limitations,
            recommended_policy_action="OBSERVE_ONLY",
            recommended_next_step="Review proxy-status and PAC/AutoConfigURL before remediation.",
        )

    evidence: list[str] = []
    if enabled:
        evidence.append("WinINET proxy is enabled.")
    if is_localhost and port:
        evidence.append(f"ProxyServer points to localhost port {port}.")

    sticky = False
    if before_snapshot is not None:
        prev_enable = before_snapshot.get("proxy_enable")
        prev_server = before_snapshot.get("proxy_server")
        if prev_enable == 0 and enabled:
            sticky = True
            evidence.append("ProxyEnable flipped from disabled to enabled since last known-good snapshot.")
        if prev_server and parsed.get("proxy_server") and prev_server != parsed.get("proxy_server"):
            evidence.append("ProxyServer changed since last known-good snapshot.")

    owner = port_owner or {}
    proc_name = _norm_name(owner.get("process_name"))
    parent_name = _norm_name(owner.get("parent_name"))
    exe_path = owner.get("executable_path")
    cmdline = owner.get("command_line")
    path_missing = not bool(exe_path)
    path_writable = _path_user_writable(str(exe_path) if exe_path else None)
    listener_match = bool(owner.get("listener_on_proxy_port"))

    if path_missing:
        evidence.append("Executable path for port owner is missing.")
    if path_writable:
        evidence.append("Executable path appears user-writable.")
    if _cmdline_has_proxy_terms(str(cmdline) if cmdline else None):
        evidence.append("Command line mentions proxy/tunnel/dev-server related terms.")
    if parent_name in _DEV_PARENT_NAMES:
        evidence.append(f"Parent process is {parent_name}.")

    category: RiskCategory = "MANUAL_LOCALHOST_PROXY"
    risk_level: RiskLevel = "MEDIUM"
    confidence = 0.55
    policy: PolicyAction = "DISABLE_WININET_PROXY"
    next_step = (
        "Preview proxy-disable, then apply with DISABLE_WININET_PROXY after review. "
        "Use proxy-stop-listener / proxy-stop-reverter only with typed Admin confirmation."
    )

    if proc_name in _SECURITY_TOOL_NAMES:
        category = "KNOWN_SECURITY_TOOL"
        risk_level = "MEDIUM"
        confidence = 0.6
        policy = "OBSERVE_ONLY"
        next_step = "Confirm intentional security tooling before disabling proxy."
    elif proc_name in _DEV_PROCESS_NAMES or parent_name in {"powershell.exe", "pwsh.exe", "cmd.exe"}:
        if listener_match:
            category = "HIGH_RISK_PROXY_TRANSITION"
            confidence = 0.65
            risk_level = "HIGH"
        else:
            category = "UNKNOWN_LOCAL_PROXY"
            confidence = 0.5
            risk_level = "MEDIUM"
    elif proc_name in {"cursor.exe", "code.exe"}:
        category = "SUSPICIOUS_LOCAL_PROXY"
        risk_level = "MEDIUM"
        confidence = 0.45
        evidence.append("IDE process correlated — low confidence; not registry writer proof.")
    elif path_missing or path_writable:
        category = "SUSPICIOUS_LOCAL_PROXY"
        risk_level = "HIGH"
        confidence = 0.6

    if sticky:
        category = "REMEDIATION_NOT_STICKY" if before_snapshot else "HIGH_RISK_PROXY_TRANSITION"
        risk_level = "HIGH"
        confidence = max(confidence, 0.7)
        policy = "TERMINATE_PROXY_REVERTER"
        next_step = (
            "Proxy re-enabled after prior disable. Stop attributed reverter parent "
            "(STOP_PROXY_REVERTER) then listener (STOP_PROXY_LISTENER), then proxy-disable with soak."
        )
    elif enabled and is_localhost and listener_match and proc_name not in _DEV_PROCESS_NAMES:
        if category == "MANUAL_LOCALHOST_PROXY":
            category = "UNKNOWN_LOCAL_PROXY"
            risk_level = "HIGH"
            confidence = 0.6

    if registry_writer_proof:
        category = "POSSIBLE_MITM_RISK"
        risk_level = "CRITICAL"
        confidence = 0.85
        evidence.append("Event-level registry write evidence present (review source).")

    return InvestigationRisk(
        category=category,
        risk_level=risk_level,
        confidence=round(min(max(confidence, 0.0), 1.0), 2),
        evidence=tuple(evidence),
        limitations=limitations,
        recommended_policy_action=policy,
        recommended_next_step=next_step,
    )

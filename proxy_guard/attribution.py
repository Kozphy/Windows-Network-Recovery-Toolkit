"""Proxy writer attribution timeline and policy gates.

The types and functions in this module intentionally separate:

* observed registry state,
* detected state change,
* listener/process correlation, and
* registry-writer proof from Sysmon, Security Event Log, Procmon, or ETW-style telemetry.

Listener correlation is emitted as ``candidate_actor`` only. It is never promoted to writer proof.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from evidence.registry_writer import RegistryWriterEvidence, WRITER_PROOF_UNAVAILABLE

EvidenceLevel = Literal["OBSERVED_STATE", "STATE_CHANGE", "CORRELATED_PROCESS", "WRITER_PROOF"]
ProxyWriterClassification = Literal[
    "MANUAL_USER_CHANGE",
    "KNOWN_BROWSER_OR_SYSTEM_COMPONENT",
    "KNOWN_VPN_OR_SECURITY_TOOL",
    "KNOWN_DEV_PROXY",
    "UNKNOWN_PROCESS_CHANGED_PROXY",
    "PROXY_CHANGED_WITH_NO_WRITER_PROOF",
    "POSSIBLE_MITM_RISK",
    "CONNECTIVITY_REGRESSED_AFTER_PROXY_CHANGE",
]
PolicyMode = Literal["ALLOW", "PREVIEW", "BLOCK"]

PROXY_FIELDS: tuple[str, ...] = (
    "ProxyEnable",
    "ProxyServer",
    "AutoConfigURL",
    "ProxyOverride",
    "AutoDetect",
)

_SIGNAL_TO_FIELD = {
    "proxy_enable": "ProxyEnable",
    "proxy_server": "ProxyServer",
    "auto_config_url": "AutoConfigURL",
    "proxy_override": "ProxyOverride",
    "auto_detect": "AutoDetect",
}
_FIELD_TO_SIGNAL = {v: k for k, v in _SIGNAL_TO_FIELD.items()}

_MANUAL_TOKENS = (
    "systemsettings.exe",
    "inetcpl.cpl",
    "control.exe",
    "rundll32.exe",
)
_BROWSER_SYSTEM_TOKENS = (
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "iexplore.exe",
    "svchost.exe",
    "explorer.exe",
    "winhttp",
    "windows defender",
    "msmpeng.exe",
)
_VPN_SECURITY_TOKENS = (
    "zscaler",
    "netskope",
    "globalprotect",
    "openvpn",
    "wireguard",
    "forticlient",
    "cisco",
    "anyconnect",
    "crowdstrike",
    "defender",
    "security",
    "vpn",
)
_DEV_PROXY_TOKENS = (
    "fiddler",
    "charles",
    "mitmproxy",
    "proxyman",
    "burp",
    "owasp",
    "zap",
    "node.exe",
    "python.exe",
    "clash",
    "v2ray",
    "shadowsocks",
)


@dataclass(frozen=True)
class ProxyAttributionEvent:
    """Timeline event for a proxy registry tuple transition.

    Attributes map directly to the requested audit model. ``candidate_listeners`` means
    correlated listener candidates, not writers. ``registry_writer_evidence`` is the only
    field that can upgrade ``evidence_level`` to ``WRITER_PROOF``.
    """

    event_id: str
    timestamp: str
    proxy_before: dict[str, Any] | None
    proxy_after: dict[str, Any]
    changed_fields: list[str]
    candidate_listeners: list[dict[str, Any]]
    registry_writer_evidence: list[dict[str, Any]]
    persistence_indicators: dict[str, Any]
    certificate_indicators: dict[str, Any]
    connectivity_before_after: dict[str, Any]
    evidence_level: EvidenceLevel
    confidence: float
    limitations: list[str]
    recommended_next_steps: list[str]
    classification: ProxyWriterClassification
    policy_gate: dict[str, Any]

    def to_jsonable(self) -> dict[str, Any]:
        """Return a JSON-ready event row for append-only audit sinks."""

        return asdict(self)


def utc_now_iso() -> str:
    """Return a UTC ISO-8601 timestamp with timezone information."""

    return datetime.now(timezone.utc).isoformat()


def proxy_tuple_from_signals(signals: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize raw collector output to the monitored WinINET proxy tuple."""

    raw = signals or {}
    return {field: raw.get(_FIELD_TO_SIGNAL[field]) for field in PROXY_FIELDS}


def diff_proxy_tuples(before: dict[str, Any] | None, after: dict[str, Any]) -> list[str]:
    """Return display field names whose values changed."""

    if before is None:
        return []
    changed: list[str] = []
    for field in PROXY_FIELDS:
        if before.get(field) != after.get(field):
            changed.append(field)
    return changed


def candidate_listeners_from_attribution(attribution: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Convert listener attribution output into explicit ``candidate_actor`` rows.

    The returned rows deliberately avoid ``writer`` terminology.
    """

    attr = attribution or {}
    out: list[dict[str, Any]] = []
    if attr.get("pid") is not None or attr.get("process_name"):
        out.append(
            {
                "role": "candidate_actor",
                "basis": "tcp_listener_on_configured_proxy_port",
                "port": attr.get("port"),
                "pid": attr.get("pid"),
                "process_name": attr.get("process_name"),
                "process_path": attr.get("process_path"),
                "parent_pid": attr.get("parent_pid"),
                "confidence": attr.get("attribution_confidence") or "low",
                "limitations": list(attr.get("limitations") or [])
                + ["Listener/process correlation does not prove registry writer identity."],
            }
        )

    for candidate in attr.get("candidate_processes") or []:
        if not isinstance(candidate, dict):
            continue
        out.append(
            {
                "role": "candidate_actor",
                "basis": "proxy_like_process_name_correlation",
                "port": attr.get("port"),
                "pid": candidate.get("pid"),
                "process_name": candidate.get("process_name"),
                "process_path": candidate.get("process_path"),
                "confidence": "low",
                "limitations": ["Process-name correlation does not prove listener ownership or registry writer identity."],
            }
        )
    return out


def _writer_evidence_to_json(evidence: list[RegistryWriterEvidence | dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in evidence:
        if isinstance(item, RegistryWriterEvidence):
            rows.append(item.to_jsonable())
        elif isinstance(item, dict):
            rows.append(dict(item))
    return rows


def determine_evidence_level(
    *,
    changed_fields: list[str],
    candidate_listeners: list[dict[str, Any]],
    registry_writer_evidence: list[dict[str, Any]],
) -> EvidenceLevel:
    """Return the strongest justified evidence level."""

    if registry_writer_evidence:
        return "WRITER_PROOF"
    if candidate_listeners:
        return "CORRELATED_PROCESS"
    if changed_fields:
        return "STATE_CHANGE"
    return "OBSERVED_STATE"


def _proxy_after_is_localhost(proxy_after: dict[str, Any], parsed_proxy: dict[str, Any] | None = None) -> bool:
    parsed = parsed_proxy or {}
    if parsed.get("is_localhost_proxy") is True:
        return True
    server = str(proxy_after.get("ProxyServer") or "").lower()
    return any(token in server for token in ("127.0.0.1", "localhost", "::1"))


def _has_persistence_indicators(persistence: dict[str, Any]) -> bool:
    count = persistence.get("persistence_entry_count")
    if isinstance(count, int) and count > 0:
        return True
    return bool(persistence.get("startup_entries") or persistence.get("scheduled_tasks") or persistence.get("run_keys"))


def _has_certificate_indicators(certificates: dict[str, Any]) -> bool:
    return bool(
        certificates.get("suspicious_certificates")
        or certificates.get("recent_root_additions")
        or certificates.get("unknown_issuer_candidates")
    )


def _connectivity_regressed(connectivity: dict[str, Any]) -> bool:
    if bool(connectivity.get("regression_detected")):
        return True
    before = connectivity.get("before") or connectivity.get("pre_change") or {}
    after = connectivity.get("after") or connectivity.get("post_change") or {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    for key in ("dns", "tcp_443", "https_direct", "https_via_proxy"):
        b = before.get(key)
        a = after.get(key)
        if isinstance(b, dict) and isinstance(a, dict) and b.get("ok") is True and a.get("ok") is False:
            return True
    return False


def _first_writer_text(writer_evidence: list[dict[str, Any]]) -> str:
    if not writer_evidence:
        return ""
    first = writer_evidence[0]
    return " ".join(
        str(first.get(k) or "")
        for k in ("process_image", "process_name", "event_source", "user")
    ).lower()


def classify_event(
    *,
    evidence_level: EvidenceLevel,
    proxy_after: dict[str, Any],
    registry_writer_evidence: list[dict[str, Any]],
    persistence_indicators: dict[str, Any],
    certificate_indicators: dict[str, Any],
    connectivity_before_after: dict[str, Any],
    parsed_proxy: dict[str, Any] | None = None,
) -> ProxyWriterClassification:
    """Classify the event without over-claiming registry writer identity."""

    if _connectivity_regressed(connectivity_before_after):
        return "CONNECTIVITY_REGRESSED_AFTER_PROXY_CHANGE"

    is_localhost = _proxy_after_is_localhost(proxy_after, parsed_proxy)
    has_risky_side_signal = _has_persistence_indicators(persistence_indicators) or _has_certificate_indicators(certificate_indicators)
    if evidence_level != "WRITER_PROOF":
        if is_localhost and has_risky_side_signal:
            return "POSSIBLE_MITM_RISK"
        return "PROXY_CHANGED_WITH_NO_WRITER_PROOF"

    writer_text = _first_writer_text(registry_writer_evidence)
    if any(token in writer_text for token in _MANUAL_TOKENS):
        return "MANUAL_USER_CHANGE"
    if any(token in writer_text for token in _VPN_SECURITY_TOKENS):
        return "KNOWN_VPN_OR_SECURITY_TOOL"
    if any(token in writer_text for token in _DEV_PROXY_TOKENS):
        return "KNOWN_DEV_PROXY"
    if any(token in writer_text for token in _BROWSER_SYSTEM_TOKENS):
        return "KNOWN_BROWSER_OR_SYSTEM_COMPONENT"
    if is_localhost and has_risky_side_signal:
        return "POSSIBLE_MITM_RISK"
    return "UNKNOWN_PROCESS_CHANGED_PROXY"


def confidence_for_level(evidence_level: EvidenceLevel, classification: str) -> float:
    """Return bounded confidence for the event-level attribution claim."""

    if evidence_level == "WRITER_PROOF":
        return 0.92 if classification != "UNKNOWN_PROCESS_CHANGED_PROXY" else 0.86
    if evidence_level == "CORRELATED_PROCESS":
        return 0.58
    if evidence_level == "STATE_CHANGE":
        return 0.42
    return 0.25


def _default_limitations(
    *,
    evidence_level: EvidenceLevel,
    changed_fields: list[str],
    writer_limitations: list[str],
    candidate_listeners: list[dict[str, Any]],
) -> list[str]:
    limitations = [
        "Observation != inference != proof.",
        "Registry polling can show state changes but cannot identify the writer process.",
    ]
    if candidate_listeners:
        limitations.append("Netstat/listener correlation identifies candidate_actor only; it is not writer proof.")
    if changed_fields and evidence_level != "WRITER_PROOF":
        limitations.append(WRITER_PROOF_UNAVAILABLE)
    limitations.extend(str(x) for x in writer_limitations if x)
    return list(dict.fromkeys(limitations))


def recommended_steps_for_event(
    *,
    evidence_level: EvidenceLevel,
    classification: ProxyWriterClassification,
) -> list[str]:
    """Return operator next steps aligned to evidence strength and policy safety."""

    if evidence_level != "WRITER_PROOF":
        return [
            "Enable Sysmon Event ID 13 registry SetValue telemetry for WinINET proxy keys or import a Procmon trace.",
            "Keep remediation in preview mode until writer evidence exists.",
            "Review candidate_actor listener processes as hypotheses, not proof.",
        ]
    if classification in {"KNOWN_DEV_PROXY", "KNOWN_VPN_OR_SECURITY_TOOL", "KNOWN_BROWSER_OR_SYSTEM_COMPONENT", "MANUAL_USER_CHANGE"}:
        return [
            "Validate the writer against approved software or user action.",
            "If restoration is needed, preview a targeted WinINET field restore and require explicit confirmation.",
        ]
    if classification == "CONNECTIVITY_REGRESSED_AFTER_PROXY_CHANGE":
        return [
            "Compare pre/post DNS, TCP 443, direct HTTPS, and proxy HTTPS checks.",
            "Investigate the writer and proxy endpoint before any restore.",
        ]
    return [
        "Manually investigate the writer process path, signer, parent process, persistence, and certificate indicators.",
        "Do not kill processes, delete certificates, reset firewall, disable adapters, or restore registry values without approval.",
    ]


def evaluate_policy_gate(
    *,
    evidence_level: EvidenceLevel,
    classification: ProxyWriterClassification,
    proxy_after: dict[str, Any],
    persistence_indicators: dict[str, Any],
    certificate_indicators: dict[str, Any],
    parsed_proxy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate conservative policy gates for writer attribution events."""

    is_localhost = _proxy_after_is_localhost(proxy_after, parsed_proxy)
    risky_side_signal = _has_persistence_indicators(persistence_indicators) or _has_certificate_indicators(certificate_indicators)
    mode: PolicyMode = "PREVIEW"
    reason = "writer_proof_unavailable_preview_only"
    matched_policy = "writer-proof-required"

    if evidence_level == "WRITER_PROOF" and classification in {
        "KNOWN_DEV_PROXY",
        "KNOWN_VPN_OR_SECURITY_TOOL",
        "KNOWN_BROWSER_OR_SYSTEM_COMPONENT",
        "MANUAL_USER_CHANGE",
    }:
        mode = "ALLOW"
        reason = "known_or_user_writer_allow_safe_restore_preview_only"
        matched_policy = "known-writer-preview-restore"
    elif evidence_level == "WRITER_PROOF" and classification == "UNKNOWN_PROCESS_CHANGED_PROXY":
        mode = "PREVIEW"
        reason = "unknown_writer_requires_manual_review"
        matched_policy = "unknown-writer-preview"

    if classification in {"POSSIBLE_MITM_RISK", "CONNECTIVITY_REGRESSED_AFTER_PROXY_CHANGE"} and is_localhost and risky_side_signal:
        mode = "BLOCK"
        reason = "unknown_or_risky_localhost_proxy_blocks_auto_remediation"
        matched_policy = "localhost-risk-block"

    return {
        "mode": mode,
        "reason": reason,
        "matched_policy": matched_policy,
        "auto_remediation_allowed": False,
        "safe_restore_preview_allowed": mode in {"ALLOW", "PREVIEW"},
        "registry_restore_requires_explicit_confirmation": True,
        "safety_controls": {
            "never_kill_process": True,
            "never_delete_certificates": True,
            "never_reset_firewall": True,
            "never_disable_adapter": True,
            "targeted_registry_restore_only": True,
        },
    }


def build_proxy_attribution_event(
    *,
    proxy_before: dict[str, Any] | None,
    proxy_after: dict[str, Any],
    candidate_listeners: list[dict[str, Any]] | None = None,
    registry_writer_evidence: list[RegistryWriterEvidence | dict[str, Any]] | None = None,
    persistence_indicators: dict[str, Any] | None = None,
    certificate_indicators: dict[str, Any] | None = None,
    connectivity_before_after: dict[str, Any] | None = None,
    writer_limitations: list[str] | None = None,
    parsed_proxy: dict[str, Any] | None = None,
    event_id: str | None = None,
    timestamp: str | None = None,
) -> ProxyAttributionEvent:
    """Build one append-only proxy writer attribution event."""

    changed = diff_proxy_tuples(proxy_before, proxy_after)
    listeners = list(candidate_listeners or [])
    writer_rows = _writer_evidence_to_json(list(registry_writer_evidence or []))
    level = determine_evidence_level(
        changed_fields=changed,
        candidate_listeners=listeners,
        registry_writer_evidence=writer_rows,
    )
    persistence = dict(persistence_indicators or {})
    certificates = dict(certificate_indicators or {})
    connectivity = dict(connectivity_before_after or {})
    classification = classify_event(
        evidence_level=level,
        proxy_after=proxy_after,
        registry_writer_evidence=writer_rows,
        persistence_indicators=persistence,
        certificate_indicators=certificates,
        connectivity_before_after=connectivity,
        parsed_proxy=parsed_proxy,
    )
    confidence = confidence_for_level(level, classification)
    limitations = _default_limitations(
        evidence_level=level,
        changed_fields=changed,
        writer_limitations=list(writer_limitations or []),
        candidate_listeners=listeners,
    )
    policy_gate = evaluate_policy_gate(
        evidence_level=level,
        classification=classification,
        proxy_after=proxy_after,
        persistence_indicators=persistence,
        certificate_indicators=certificates,
        parsed_proxy=parsed_proxy,
    )
    return ProxyAttributionEvent(
        event_id=event_id or str(uuid.uuid4()),
        timestamp=timestamp or utc_now_iso(),
        proxy_before=None if proxy_before is None else dict(proxy_before),
        proxy_after=dict(proxy_after),
        changed_fields=changed,
        candidate_listeners=listeners,
        registry_writer_evidence=writer_rows,
        persistence_indicators=persistence,
        certificate_indicators=certificates,
        connectivity_before_after=connectivity,
        evidence_level=level,
        confidence=confidence,
        limitations=limitations,
        recommended_next_steps=recommended_steps_for_event(evidence_level=level, classification=classification),
        classification=classification,
        policy_gate=policy_gate,
    )


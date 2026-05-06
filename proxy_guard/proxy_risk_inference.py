"""Pure proxy hijack and MITM risk inference logic.

The functions in this module are deterministic and side-effect free. Collectors provide observed
signals; this layer converts those observations into bounded inferences, validation gaps, and an
operator-facing decision. Heuristic attribution is never treated as proof of compromise.
"""

from __future__ import annotations

from typing import Any

KNOWN_DEV_PROCESS_NAMES = {"mitmproxy.exe", "fiddler.exe", "charles.exe", "proxyman.exe", "node.exe", "python.exe"}
KNOWN_SECURITY_PROCESS_NAMES = {
    "zscaler.exe",
    "zsatunnel.exe",
    "netskope.exe",
    "defenderforendpoint.exe",
    "symantec.exe",
    "crowdstrike.exe",
    "csfalconservice.exe",
}
DEV_PATH_HINTS = (
    "\\program files\\nodejs\\",
    "\\program files\\python",
    "\\python",
    "\\mitmproxy",
    "\\fiddler",
    "\\charles",
    "\\proxyman",
)
SECURITY_PATH_HINTS = ("\\zscaler\\", "\\netskope\\", "\\crowdstrike\\", "\\symantec\\", "\\windows defender\\")
USER_SPACE_PATH_HINTS = ("\\appdata\\", "\\temp\\", "\\downloads\\", "\\users\\public\\")


def _clamp(value: float) -> float:
    """Clamp a score to the closed interval [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def _risk_level(score: float) -> str:
    """Convert a numeric score into a user-facing risk level."""
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _lower(value: Any) -> str:
    """Return a lowercase string for optional values."""
    return str(value or "").lower()


def _path_contains(path: str | None, hints: tuple[str, ...]) -> bool:
    """Return whether a path contains any normalized hint."""
    lower_path = _lower(path)
    return bool(lower_path and any(hint in lower_path for hint in hints))


def _is_known_dev_context(process_name: str, process_path: str | None) -> bool:
    """Return whether process metadata looks like normal developer proxy tooling."""
    if process_name not in KNOWN_DEV_PROCESS_NAMES:
        return False
    if process_name in {"fiddler.exe", "charles.exe", "mitmproxy.exe", "proxyman.exe"}:
        return True
    return _path_contains(process_path, DEV_PATH_HINTS) and not _path_contains(process_path, USER_SPACE_PATH_HINTS)


def _is_known_security_context(process_name: str, process_path: str | None) -> bool:
    """Return whether process metadata looks like a known security/enterprise proxy tool."""
    return process_name in KNOWN_SECURITY_PROCESS_NAMES or _path_contains(process_path, SECURITY_PATH_HINTS)


def _collection_to_text(value: Any) -> str:
    """Convert nested collector output to searchable lowercase text."""
    return _lower(value)


def _persistence_references_process(persistence: dict[str, Any], process_name: str, process_path: str | None) -> bool:
    """Return whether startup surfaces reference the attributed process."""
    if not process_name and not process_path:
        return False
    blob = _collection_to_text(persistence.get("startup_entries"))
    blob += _collection_to_text(persistence.get("scheduled_tasks"))
    blob += _collection_to_text(persistence.get("run_keys"))
    return bool((process_name and process_name in blob) or (process_path and process_path.lower() in blob))


def _has_any_persistence(persistence: dict[str, Any]) -> bool:
    """Return whether persistence collectors saw any startup/task/run-key entries."""
    count = persistence.get("persistence_entry_count")
    if isinstance(count, int):
        return count > 0
    return bool(persistence.get("startup_entries") or persistence.get("scheduled_tasks") or persistence.get("run_keys"))


def _combine_limitations(*sources: dict[str, Any], extra: list[str] | None = None) -> list[str]:
    """Combine and de-duplicate limitations from collectors and inference."""
    ordered: list[str] = []
    for item in extra or []:
        if item not in ordered:
            ordered.append(item)
    for source in sources:
        for limitation in source.get("limitations") or []:
            text = str(limitation)
            if text not in ordered:
                ordered.append(text)
    return ordered


def _base_recommendations() -> list[str]:
    """Return default operator validation actions."""
    return [
        "Inspect process path and parent process",
        "Check startup entries",
        "Verify trusted root certificates",
        "Temporarily disable proxy only after user confirmation",
    ]


def infer_proxy_risk(
    *,
    proxy_signals: dict[str, Any],
    attribution: dict[str, Any],
    persistence: dict[str, Any],
    certificates: dict[str, Any],
    traffic_modification_evidence: bool = False,
) -> dict[str, Any]:
    """Infer proxy-hijack and MITM risk from collected observations.

    Args:
        proxy_signals: WinINET proxy observations from ``proxy_signal_collector``.
        attribution: Port-to-process correlation from ``port_process_attribution``.
        persistence: Startup/task/run-key preview data.
        certificates: Trusted-root certificate preview data.
        traffic_modification_evidence: External validation flag indicating content rewrite,
            unexpected certificate substitution, or similar observed traffic modification.

    Returns:
        Classification payload with score, confidence, reasons, limitations, recommended actions,
        and a structured evidence section.
    """
    observations: list[str] = []
    inferences: list[str] = []
    validations: list[str] = []
    limitations: list[str] = [
        "Heuristic attribution is not proof of compromise.",
        "Port listener attribution does not prove registry writer identity.",
        "Registry polling cannot prove exact modification actor.",
    ]
    reasons: list[str] = []
    recommended_actions = _base_recommendations()
    score = 0.0
    confidence = 0.62

    proxy_enable_value = proxy_signals.get("proxy_enable")
    proxy_enable = int(proxy_enable_value or 0)
    proxy_server = proxy_signals.get("proxy_server")
    auto_config_url = proxy_signals.get("auto_config_url")
    parsed = proxy_signals.get("parsed_proxy") or {}
    is_localhost_proxy = bool(parsed.get("is_localhost_proxy"))

    observations.extend(str(item) for item in proxy_signals.get("observations") or [])
    if proxy_enable_value is None:
        limitations.append("ProxyEnable was not observed; no-proxy decision has reduced confidence.")
        return {
            "classification": "NO_PROXY",
            "risk_score": 0.0,
            "risk_level": "low",
            "confidence": 0.38,
            "reasons": ["WinINET ProxyEnable was not observed; no enabled proxy signal was validated."],
            "limitations": _combine_limitations(proxy_signals, extra=limitations),
            "recommended_actions": ["Run this diagnostic on Windows to inspect WinINET proxy state."],
            "evidence": {
                "observations": observations,
                "inferences": ["No enabled WinINET proxy was inferred from available signals."],
                "validations": ["Validate on a Windows endpoint before treating this as absence of proxy risk."],
                "decision": {"classification": "NO_PROXY", "risk_level": "low"},
            },
        }

    if proxy_enable == 0:
        reason = "WinINET proxy is disabled."
        if auto_config_url:
            limitations.append("AutoConfigURL is present but static proxy scoring treats ProxyEnable=0 as no static proxy.")
            reason = f"{reason} AutoConfigURL is configured and should be validated separately."
        return {
            "classification": "NO_PROXY",
            "risk_score": 0.0,
            "risk_level": "low",
            "confidence": 0.92,
            "reasons": [reason],
            "limitations": _combine_limitations(proxy_signals, persistence, certificates, extra=limitations),
            "recommended_actions": ["No static WinINET proxy hijack signal observed. Continue periodic monitoring."],
            "evidence": {
                "observations": observations,
                "inferences": ["No enabled static WinINET proxy was inferred."],
                "validations": ["Review PAC/AutoConfigURL separately when enterprise proxy policy uses PAC files."]
                if auto_config_url
                else [],
                "decision": {"classification": "NO_PROXY", "risk_level": "low"},
            },
        }

    score += 0.22
    observations.append(f"WinINET proxy enabled: {proxy_server or '<empty>'}")
    reasons.append(f"WinINET proxy enabled: {proxy_server or '<empty>'}")
    if is_localhost_proxy:
        score += 0.1
        observations.append("ProxyServer points to localhost/loopback endpoint.")
        reasons.append("ProxyServer points to localhost/loopback endpoint.")
    else:
        score += 0.25
        inferences.append("ProxyServer does not point to a localhost endpoint and may route traffic externally.")
        reasons.append("ProxyServer does not point to a localhost endpoint.")

    process_name = _lower(attribution.get("process_name"))
    process_path = attribution.get("process_path")
    attribution_confidence = _lower(attribution.get("attribution_confidence") or "low")
    pid = attribution.get("pid")
    observations.extend(str(item) for item in attribution.get("observations") or [])

    if pid is not None:
        reasons.append(f"Proxy port is bound by {attribution.get('process_name')} (PID {pid}).")
        confidence += 0.16 if attribution_confidence == "high" else 0.08
    elif process_name:
        score += 0.12
        confidence -= 0.08
        reasons.append(f"Only process-name correlation was available: {attribution.get('process_name')}.")
        limitations.append("Process-name correlation does not prove the process owns the configured proxy port.")
    else:
        score += 0.16
        confidence -= 0.18
        reasons.append("Could not attribute proxy listener process.")
        limitations.append("No listener PID resolved for configured proxy port.")

    known_dev = _is_known_dev_context(process_name, process_path)
    known_security = _is_known_security_context(process_name, process_path)
    user_space_path = _path_contains(process_path, USER_SPACE_PATH_HINTS)
    path_known = bool(process_path)

    if known_security:
        score += 0.04
        inferences.append("Attributed process resembles a known security or enterprise proxy tool.")
        reasons.append("Attributed process resembles a known security or enterprise proxy tool.")
        validations.append("Validate this process against approved endpoint security tooling.")
    elif known_dev:
        score += 0.05
        inferences.append("Attributed process resembles normal developer proxy tooling.")
        reasons.append("Attributed process resembles normal developer proxy tooling.")
        validations.append("Confirm the developer proxy was intentionally started by the user.")
    elif process_name:
        score += 0.18
        inferences.append("Attributed process is not in the known developer or security tool set.")
        reasons.append("Attributed process is not in the known developer or security tool set.")

    if user_space_path:
        score += 0.24
        reasons.append("Process path is unknown or user-space AppData/temp/downloads location.")
        inferences.append("User-space executable path raises persistence and tampering risk.")
    elif path_known:
        reasons.append(f"Process path resolved: {process_path}")
        observations.append(f"Process path observed: {process_path}")
    else:
        score += 0.1
        confidence -= 0.07
        reasons.append("Process path is unknown or unavailable.")
        limitations.append("Process executable path was not resolved; attribution confidence is reduced.")

    if _persistence_references_process(persistence, process_name, str(process_path) if process_path else None):
        score += 0.18
        reasons.append("Startup persistence detected for the attributed process.")
        inferences.append("Proxy process appears to have an auto-start path.")
        validations.append("Review the specific startup entry before removing or disabling anything.")
    elif _has_any_persistence(persistence):
        observations.append("Persistence surfaces were inspected and contain entries.")
        reasons.append("Persistence surfaces inspected; no direct reference to the attributed process was inferred.")

    suspicious_certs = certificates.get("suspicious_certificates") or []
    recent_roots = certificates.get("recent_root_additions") or []
    unknown_issuers = certificates.get("unknown_issuer_candidates") or []
    if suspicious_certs:
        score += 0.25
        reasons.append(f"Suspicious trusted-root certificate indicators found: {len(suspicious_certs)}.")
        inferences.append("Trusted-root indicators may support a browser traffic interception hypothesis.")
        validations.append("Validate suspicious root certificates against enterprise PKI policy.")
    if recent_roots:
        score += 0.07
        reasons.append("Recent trusted-root NotBefore indicators detected.")
        validations.append("Confirm certificate install time with endpoint logs if available.")
    if unknown_issuers and not suspicious_certs:
        score += 0.04
        reasons.append("Unknown trusted-root issuer candidates were observed.")
        validations.append("Treat unknown issuer names as validation prompts, not compromise proof.")
    if traffic_modification_evidence:
        score += 0.24
        reasons.append("Traffic modification evidence present from external validation.")
        inferences.append("Traffic validation strengthens the possible MITM risk hypothesis.")

    has_mitm_indicator = bool(suspicious_certs or traffic_modification_evidence)
    if has_mitm_indicator and score >= 0.65:
        classification = "POSSIBLE_MITM_RISK"
    elif score >= 0.65 or (not is_localhost_proxy and proxy_enable == 1):
        classification = "SUSPICIOUS_PROXY"
    elif known_security:
        classification = "KNOWN_SECURITY_TOOL"
    elif known_dev:
        classification = "KNOWN_DEV_PROXY"
    elif is_localhost_proxy:
        classification = "UNKNOWN_LOCAL_PROXY"
    else:
        classification = "SUSPICIOUS_PROXY"

    if (
        classification == "KNOWN_DEV_PROXY"
        and not _persistence_references_process(persistence, process_name, str(process_path) if process_path else None)
        and not suspicious_certs
        and not recent_roots
        and not traffic_modification_evidence
    ):
        score = min(score, 0.32)
    if (
        classification == "KNOWN_SECURITY_TOOL"
        and not _persistence_references_process(persistence, process_name, str(process_path) if process_path else None)
        and not suspicious_certs
        and not traffic_modification_evidence
    ):
        score = min(score, 0.34)

    if classification == "POSSIBLE_MITM_RISK":
        recommended_actions.insert(0, "Validate browser certificate chain for a known HTTPS site")
    if classification in {"SUSPICIOUS_PROXY", "POSSIBLE_MITM_RISK", "UNKNOWN_LOCAL_PROXY"}:
        recommended_actions.append("Capture a fresh scan after closing expected developer tools")
    if pid is None and is_localhost_proxy:
        recommended_actions.append("Validate whether localhost proxy listener exists during active browser traffic")

    score = _clamp(score)
    confidence = _clamp(confidence)
    risk_level = _risk_level(score)
    limitations = _combine_limitations(proxy_signals, attribution, persistence, certificates, extra=limitations)
    decision = {
        "classification": classification,
        "risk_score": round(score, 2),
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
    }
    return {
        "classification": classification,
        "risk_score": round(score, 2),
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "limitations": limitations,
        "recommended_actions": recommended_actions,
        "evidence": {
            "observations": observations,
            "inferences": inferences,
            "validations": validations,
            "decision": decision,
        },
    }


__all__ = ["infer_proxy_risk"]

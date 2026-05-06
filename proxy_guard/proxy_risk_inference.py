"""Pure proxy risk inference logic for security diagnostics."""

from __future__ import annotations

from typing import Any

KNOWN_DEV_PROCESSES = {"mitmproxy.exe", "fiddler.exe", "charles.exe", "node.exe", "python.exe"}
KNOWN_SECURITY_TOOLS = {"zscaler.exe", "netskope.exe", "defenderforendpoint.exe", "symantec.exe", "crowdstrike.exe"}


def _contains_user_space_path(path: str | None) -> bool:
    if not path:
        return False
    lower = path.lower()
    return "\\appdata\\" in lower or "\\temp\\" in lower or "\\downloads\\" in lower


def _risk_level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def infer_proxy_risk(
    *,
    proxy_signals: dict[str, Any],
    attribution: dict[str, Any],
    persistence: dict[str, Any],
    certificates: dict[str, Any],
    traffic_modification_evidence: bool = False,
) -> dict[str, Any]:
    """Infer proxy-hijack and MITM risk from collected signals.

    Returns:
        Stable classification payload with score, confidence, reasons, limitations, and actions.
    """
    reasons: list[str] = []
    limitations: list[str] = [
        "Port listener attribution does not prove registry writer identity",
        "Registry polling cannot prove exact modification actor",
    ]
    recs: list[str] = []
    score = 0.0
    confidence = 0.55

    proxy_enable = int(proxy_signals.get("proxy_enable") or 0)
    parsed = proxy_signals.get("parsed_proxy") or {}
    proxy_server = proxy_signals.get("proxy_server")

    if proxy_enable == 0:
        return {
            "classification": "NO_PROXY",
            "risk_score": 0.0,
            "risk_level": "low",
            "confidence": 0.92,
            "reasons": ["WinINET proxy is disabled."],
            "limitations": limitations,
            "recommended_actions": ["No proxy hijack signal observed. Continue periodic monitoring."],
        }

    reasons.append(f"WinINET proxy enabled: {proxy_server}")
    score += 0.25
    if parsed.get("is_localhost_proxy"):
        score += 0.1
        reasons.append("ProxyServer points to localhost/loopback endpoint.")

    pname = str(attribution.get("process_name") or "").lower()
    ppath = attribution.get("process_path")
    conf = str(attribution.get("attribution_confidence") or "low")
    if attribution.get("pid") is not None:
        reasons.append(f"Proxy port attribution candidate: {attribution.get('process_name')} (PID {attribution.get('pid')}).")
    else:
        reasons.append("Could not attribute proxy listener process.")
        limitations.append("No listener PID resolved for configured proxy port.")
        score += 0.12
        confidence -= 0.18

    if conf == "high":
        confidence += 0.18
    elif conf == "medium":
        confidence += 0.08
    else:
        confidence -= 0.08

    if pname in KNOWN_SECURITY_TOOLS:
        classification = "KNOWN_SECURITY_TOOL"
        score += 0.05
    elif pname in KNOWN_DEV_PROCESSES:
        classification = "KNOWN_DEV_PROXY"
        score += 0.08 if pname == "node.exe" else 0.03
    elif parsed.get("is_localhost_proxy"):
        classification = "UNKNOWN_LOCAL_PROXY"
        score += 0.2
    else:
        classification = "SUSPICIOUS_PROXY"
        score += 0.3

    if _contains_user_space_path(ppath):
        score += 0.2
        reasons.append("Process path appears in user-space/AppData/temp location.")
    elif ppath:
        reasons.append(f"Process path resolved: {ppath}")
    else:
        reasons.append("Process path unavailable.")
        limitations.append("Process executable path not resolved; attribution confidence reduced.")
        score += 0.08

    startup_blob = (
        str(persistence.get("startup_entries") or "")
        + str(persistence.get("scheduled_tasks") or "")
        + str((persistence.get("run_keys") or {}).get("hkcu") or "")
        + str((persistence.get("run_keys") or {}).get("hklm") or "")
    ).lower()
    if pname and pname in startup_blob:
        score += 0.18
        reasons.append("Startup persistence indicator references attributed process.")
    elif startup_blob.strip():
        reasons.append("Persistence surfaces inspected (startup/tasks/run keys).")

    suspicious_certs = certificates.get("suspicious_certificates") or []
    if suspicious_certs:
        score += 0.25
        reasons.append(f"Suspicious root certificate indicators found: {len(suspicious_certs)}")
    if certificates.get("recent_root_additions"):
        score += 0.07
        reasons.append("Recent trusted-root additions detected (needs validation).")
    if traffic_modification_evidence:
        score += 0.2
        reasons.append("Traffic modification evidence present from external validation.")

    if score >= 0.78 and (suspicious_certs or traffic_modification_evidence):
        classification = "POSSIBLE_MITM_RISK"
    elif score >= 0.62 and classification in {"UNKNOWN_LOCAL_PROXY", "SUSPICIOUS_PROXY"}:
        classification = "SUSPICIOUS_PROXY"

    score = max(0.0, min(1.0, score))
    confidence = max(0.0, min(1.0, confidence))

    recs.extend(
        [
            "Inspect process path and parent process",
            "Check startup entries",
            "Verify trusted root certificates",
            "Temporarily disable proxy only after user confirmation",
        ]
    )
    if parsed.get("is_localhost_proxy") and attribution.get("pid") is None:
        recs.append("Validate whether localhost proxy listener exists during active browser traffic.")
    return {
        "classification": classification,
        "risk_score": round(score, 2),
        "risk_level": _risk_level(score),
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "limitations": limitations + list(proxy_signals.get("limitations") or []) + list(attribution.get("limitations") or []),
        "recommended_actions": recs,
    }


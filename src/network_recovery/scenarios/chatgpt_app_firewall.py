"""CASE_CHATGPT_APP_FIREWALL_FILTERING_INTERACTION scenario analyzer.

Module responsibility:
    Rank competing hypotheses when browser path is healthy but ChatGPT/app path degrades.

System placement:
    Called by ``engine.run_scenario_diagnosis`` after ``collect_signals``.

Key invariants:
    * Ordinal confidence only; sorted high > medium > low.
    * Never emits malware or attack verdicts.
    * ``recovery_firewall_reset_helped`` adjusts verification_status only.

Decision intent:
    Triage firewall, Electron, cache/session, proxy/VPN interactions for operator review.

Audit Notes:
    * Verify ranked hypotheses against raw ``SignalBundle`` in audit JSONL.
    * Recovery feedback via ``--recovery-feedback firewall_reset_helped`` on CLI.
"""

from __future__ import annotations

from ..app_state import PROCESS_FANOUT_REVIEW_THRESHOLD
from ..models import (
    CASE_CHATGPT_APP_FIREWALL_FILTERING_INTERACTION,
    DESKTOP_APP_PATH_DEGRADED_EVENT,
    SCENARIO_CHATGPT_APP_FIREWALL,
    RankedHypothesis,
    SignalBundle,
)


def _browser_healthy_app_degraded(signals: SignalBundle) -> bool:
    if signals.browser_https_ok is not True:
        return False
    app_fail = signals.chatgpt_https_ok is False or (
        signals.chatgpt_process_detected and signals.chatgpt_https_ok is not True
    )
    return app_fail


def _rank_hypotheses(
    signals: SignalBundle,
    *,
    recovery_firewall_reset_helped: bool | None,
) -> list[RankedHypothesis]:
    rows: list[RankedHypothesis] = []

    proxy_enabled = signals.wininet_proxy_enable == 1
    loopback = bool(signals.localhost_listener_ports) or (
        proxy_enabled
        and signals.wininet_proxy_server
        and "127." in (signals.wininet_proxy_server or "")
    )

    fw_for: list[str] = []
    fw_against: list[str] = []
    if recovery_firewall_reset_helped is True:
        fw_for.append("Operator reported firewall reset restored ChatGPT/desktop app connectivity.")
    if signals.browser_https_ok and signals.curl_https_ok and signals.chatgpt_https_ok is False:
        fw_for.append("Browser/curl HTTPS OK while ChatGPT/OpenAI HTTPS probe failed.")
    if signals.dns_ok is False:
        fw_against.append("DNS probe failed — may be broader than firewall filtering alone.")
    rows.append(
        RankedHypothesis(
            hypothesis_id="firewall_filtering_interaction",
            confidence="high"
            if recovery_firewall_reset_helped
            else ("medium" if fw_for else "low"),
            evidence_for=tuple(fw_for),
            evidence_against=tuple(fw_against),
            limitations=(
                "Recovery evidence supports a filtering interaction hypothesis; it is not proof of attack or malware.",
                "Firewall rule inspection still required for root cause.",
            ),
        )
    )

    el_for: list[str] = []
    if signals.chatgpt_process_detected or signals.electron_process_detected:
        el_for.append("ChatGPT/Electron process detected while app-path HTTPS probe failed.")
    if signals.browser_https_ok and signals.chatgpt_https_ok is False:
        el_for.append("System browser path healthy; desktop app path degraded.")
    rows.append(
        RankedHypothesis(
            hypothesis_id="electron_network_stack_issue",
            confidence="medium" if el_for else "low",
            evidence_for=tuple(el_for),
            evidence_against=(),
            limitations=("Electron stack issues are inferred; no ETW capture in this scenario.",),
        )
    )

    cache_for: list[str] = []
    cache_against: list[str] = []
    if signals.chatgpt_process_detected and signals.chatgpt_https_ok is False:
        cache_for.append(
            "App running but HTTPS probe to ChatGPT endpoints failed — may be session/cache."
        )
    high_fanout = (
        signals.chatgpt_process_count is not None
        and signals.chatgpt_process_count >= PROCESS_FANOUT_REVIEW_THRESHOLD
    )
    state_observed = bool(signals.chatgpt_network_state_file_count)
    if high_fanout:
        cache_for.append(
            f"Observed {signals.chatgpt_process_count} ChatGPT.exe process rows while the app path "
            "was degraded; this is a review threshold, not proof the processes are hung."
        )
    elif signals.chatgpt_process_count is not None:
        cache_against.append(
            f"Observed process count ({signals.chatgpt_process_count}) is below the "
            f"{PROCESS_FANOUT_REVIEW_THRESHOLD}-process review threshold."
        )
    if state_observed:
        cache_for.append(
            "A bounded Chromium Network Persistent State artifact was observed; its presence is "
            "normal and does not prove corruption."
        )
    rows.append(
        RankedHypothesis(
            hypothesis_id="app_cache_or_session_issue",
            confidence="medium" if high_fanout and state_observed else "low",
            evidence_for=tuple(cache_for),
            evidence_against=tuple(cache_against),
            limitations=(
                "Process fan-out does not prove processes are stuck or identify a cause.",
                "Network-state file presence does not prove cached QUIC or Happy Eyeballs corruption.",
                "Cold restart and quarantine are recovery tests, not confirmation of cache root cause.",
            ),
        )
    )

    px_for: list[str] = []
    if loopback:
        px_for.append("Loopback proxy listener or WinINET localhost proxy segment observed.")
    if signals.winhttp_loopback_hint:
        px_for.append("WinHTTP shows loopback proxy hints.")
    rows.append(
        RankedHypothesis(
            hypothesis_id="proxy_or_localhost_proxy_interaction",
            confidence="high"
            if loopback and signals.chatgpt_https_ok is False
            else ("medium" if loopback else "low"),
            evidence_for=tuple(px_for),
            evidence_against=(),
            limitations=(
                "Listener correlation does not prove which process wrote proxy registry keys.",
            ),
        )
    )

    vpn_for: list[str] = []
    if signals.vpn_adapter_hint:
        vpn_for.append("VPN/TUN-style adapter description detected.")
    rows.append(
        RankedHypothesis(
            hypothesis_id="vpn_or_security_filter_driver_interaction",
            confidence="medium" if vpn_for else "low",
            evidence_for=tuple(vpn_for),
            evidence_against=(),
            limitations=("VPN/filter driver presence is observational only.",),
        )
    )

    rank_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }
    rows.sort(key=lambda h: (rank_order[h.confidence], h.hypothesis_id))
    return rows


def analyze_chatgpt_app_firewall(
    signals: SignalBundle,
    *,
    recovery_firewall_reset_helped: bool | None = None,
) -> dict[str, object]:
    """Return events, ranked hypotheses, verification, and confidence boundary.

    Args:
        signals: Observation bundle from collectors.
        recovery_firewall_reset_helped: Optional post-remediation operator feedback.

    Returns:
        Dict with keys: canonical_case, scenario_id, events, hypotheses,
        verification_status, confidence_boundary, limitations.
    """
    events: list[str] = []
    if _browser_healthy_app_degraded(signals):
        events.append(DESKTOP_APP_PATH_DEGRADED_EVENT)

    hypotheses = _rank_hypotheses(
        signals, recovery_firewall_reset_helped=recovery_firewall_reset_helped
    )

    if recovery_firewall_reset_helped is True:
        verification_status = "supported_by_recovery_evidence"
    elif recovery_firewall_reset_helped is False:
        verification_status = "contradicted_by_recovery_evidence"
    else:
        verification_status = "not_run"

    confidence_boundary = (
        "Ordinal confidence ranks competing hypotheses; not a calibrated probability. "
        "Observation ≠ inference ≠ proof."
    )

    limitations = [
        "Do not claim malware, attack, or surveillance without explicit forensic evidence tier.",
        "Process and listener signals are correlation only unless registry-writer telemetry exists.",
        *list(signals.collector_notes),
    ]

    return {
        "canonical_case": CASE_CHATGPT_APP_FIREWALL_FILTERING_INTERACTION,
        "scenario_id": SCENARIO_CHATGPT_APP_FIREWALL,
        "events": events,
        "hypotheses": hypotheses,
        "verification_status": verification_status,
        "confidence_boundary": confidence_boundary,
        "limitations": limitations,
    }

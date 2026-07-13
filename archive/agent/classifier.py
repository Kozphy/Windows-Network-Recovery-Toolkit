"""Rule-based classifier for the standalone ``agent`` CLI (collector → classify → plan).

Produces confidence-ranked ``RankedCause`` rows from ``DiagnosticEvidence`` using the same
spirit as ``src/decision_engine`` but keyed to agent-specific categories consumed by
`agent.planner`. Pure Python: no persistence or outbound calls in this module.

Audit Notes:
    Compare ranked explanations against raw collector output whenever recommendations look
    wrong; stale netstat spikes can falsely elevate exhaustion scores."""

from __future__ import annotations

from .schemas import DiagnosticEvidence, RankedCause, RootCauseCategory

_CONNECTION_SPIKE_TW = 5000
_CONNECTION_SPIKE_EST = 8000


def _clamp(score: float) -> float:
    """Clamp confidence score to [0.0, 1.0]."""
    return max(0.0, min(1.0, score))


def classify(evidence: DiagnosticEvidence) -> list[RankedCause]:
    """Rank root-cause hypotheses from collected evidence.

    Decision intent:
        Produce explainable confidence-ranked hypotheses that drive remediation
        planning while preserving conservative safety defaults.

    Constraints and limitations:
        - Rule-based heuristics can underperform for uncommon edge conditions.
        - Competing failures may produce close confidence scores.

    Audit Notes:
        - What can go wrong: misclassification under mixed or stale signals.
        - Detection: inspect ranked explanations and raw evidence together.
        - Recovery: rerun collector and compare with monitor trends.

    Args:
        evidence: Normalized diagnostic evidence snapshot.

    Returns:
        list[RankedCause]: Deduplicated hypotheses sorted by confidence.
    """
    candidates: list[RankedCause] = []

    # Connection exhaustion / leaks — checked early when counters dominate.
    exhaustion_signal = (
        evidence.time_wait_count >= _CONNECTION_SPIKE_TW
        or evidence.established_count >= _CONNECTION_SPIKE_EST
    )
    if exhaustion_signal:
        ratio_tw = min(1.0, evidence.time_wait_count / max(_CONNECTION_SPIKE_TW, 1))
        ratio_es = min(1.0, evidence.established_count / max(_CONNECTION_SPIKE_EST, 1))
        conf = _clamp(0.55 + 0.35 * max(ratio_tw, ratio_es))
        candidates.append(
            RankedCause(
                category="connection_exhaustion",
                confidence=conf,
                explanation=(
                    f"Elevated TIME_WAIT ({evidence.time_wait_count}) or ESTABLISHED "
                    f"({evidence.established_count}) suggests ephemeral port pressure or leaks."
                ),
            )
        )

    # Layer 1: reachability
    if not evidence.ping_ok:
        candidates.append(
            RankedCause(
                category="tcp_issue",
                confidence=0.88,
                explanation="ICMP to a well-known host failed; general IP reachability is impaired.",
            )
        )

    # DNS
    if evidence.ping_ok and not evidence.dns_ok:
        candidates.append(
            RankedCause(
                category="dns_issue",
                confidence=0.86,
                explanation="Ping succeeds but DNS resolution failed; resolver or DNS path issue.",
            )
        )

    # Proxy vs HTTPS (WinHTTP / user proxy aligned with batch toolkit semantics)
    proxy_like = evidence.user_proxy_enabled or ("Direct access" not in evidence.winhttp_proxy_summary)
    if proxy_like and not evidence.https_ok:
        candidates.append(
            RankedCause(
                category="proxy_issue",
                confidence=0.84,
                explanation=(
                    "Proxy configuration appears active or WinHTTP is not direct access, "
                    "while HTTPS fails — consistent with proxy misrouting."
                ),
            )
        )

    # TLS / certificate
    if evidence.tls_cert_issue_detected:
        candidates.append(
            RankedCause(
                category="tls_cert_issue",
                confidence=0.72,
                explanation="curl/TLS output hints at certificate or TLS handshake problems.",
            )
        )

    # HTTPS without TLS hint — transport path / filtering
    if (
        evidence.ping_ok
        and evidence.dns_ok
        and evidence.tcp_443_ok
        and not evidence.https_ok
        and not evidence.tls_cert_issue_detected
    ):
        candidates.append(
            RankedCause(
                category="https_issue",
                confidence=0.68,
                explanation=(
                    "TCP 443 succeeds but HTTPS layer fails without explicit TLS cert markers — "
                    "inspect HTTPS filtering, inspection proxies, or AV SSL scanning."
                ),
            )
        )

    # TCP path when ping ok but 443 fails
    if evidence.ping_ok and evidence.dns_ok and not evidence.tcp_443_ok:
        candidates.append(
            RankedCause(
                category="tcp_issue",
                confidence=0.70,
                explanation="TCP 443 to a common endpoint failed while basic DNS works.",
            )
        )

    # Winsock / stack corruption heuristic — broad failures across layers
    broad_failure = (
        not evidence.ping_ok
        and not evidence.dns_ok
        and not evidence.tcp_443_ok
        and not evidence.https_ok
    )
    if broad_failure:
        candidates.append(
            RankedCause(
                category="winsock_issue",
                confidence=0.55,
                explanation=(
                    "Multiple independent probes failed together — consistent with stack/driver corruption "
                    "(confirm hardware/link before repair)."
                ),
            )
        )

    # Firewall — conservative; never implies automatic reset in planner.
    if evidence.firewall_blocking_suspected:
        candidates.append(
            RankedCause(
                category="firewall_issue",
                confidence=0.45,
                explanation=(
                    "Heuristic: TCP path OK but HTTPS fails, or proxy output mentions blocking — "
                    "review firewall rules manually; automated firewall reset is disabled."
                ),
            )
        )

    if not candidates:
        candidates.append(
            RankedCause(
                category="unknown",
                confidence=0.35,
                explanation="No strong pattern matched; gather more evidence or monitor over time.",
            )
        )

    # De-duplicate categories keeping highest confidence
    best: dict[RootCauseCategory, RankedCause] = {}
    for c in candidates:
        prev = best.get(c.category)
        if prev is None or c.confidence > prev.confidence:
            best[c.category] = c

    ranked = sorted(best.values(), key=lambda x: x.confidence, reverse=True)
    return ranked


def classify_with_primary(evidence: DiagnosticEvidence) -> tuple[RankedCause | None, list[RankedCause]]:
    """Return primary hypothesis and ranked list for planner/executor stages.

    Args:
        evidence: Normalized diagnostic evidence snapshot.

    Returns:
        tuple[RankedCause | None, list[RankedCause]]: Primary cause (or ``None``
        when classifier yields no candidates) and full ranked hypotheses.

    Raises:
        None.

    Audit Notes:
        When primary is unexpectedly ``None``, review `classify` output and raw
        evidence JSON before executing repair steps downstream.
    """
    ranked = classify(evidence)
    primary = ranked[0] if ranked else None
    return primary, ranked

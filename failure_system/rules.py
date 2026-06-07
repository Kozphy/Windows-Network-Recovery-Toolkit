"""Deterministic rule engine mapping diagnostic booleans to ranked explanations.

Decision intent:
    Hypothesize likely failure families (DNS vs HTTPS-path vs proxy vs link) using only the
    normalized booleans inside ``DiagnosticSnapshot``—no ML, no historical correlation.

Inputs:
    ``DiagnosticSnapshot`` fields produced by ``collector.collect_diagnostics``.

Constraints:
    Rules may overlap (for example proxy hints alongside HTTPS failures); callers sort by
    ``confidence`` descending and surface the top rows first.

Audit Notes:
    Review stored ``RuleOutcome.explanation`` strings beside raw probe output when disputing a
    classification; rerun diagnostics after environmental changes.

Recovery guidance:
    If classifications disagree with ground truth, extend collector probes or tighten heuristics
    rather than mutating persisted FailureBlocks manually.
"""

from __future__ import annotations

from failure_system.models import DiagnosticSnapshot, RuleOutcome


class RuleEngine:
    """Evaluate ordered deterministic hypotheses over one diagnostic snapshot."""

    def evaluate(self, snapshot: DiagnosticSnapshot) -> list[RuleOutcome]:
        """Emit every rule whose predicates match, sorted by descending confidence.

        Args:
            snapshot: Normalized probe booleans and metadata from ``collect_diagnostics``.

        Returns:
            Sorted ``RuleOutcome`` list (highest confidence first). Typical snapshots emit multiple
            overlapping hypotheses plus an optional low-salience baseline rule.

        Engineering Notes:
            Confidence literals are static weights tuned for readability, not calibrated ML scores.

        Audit Notes:
            The healthy ``baseline_ok`` rule is intentionally low confidence and may co-exist with
            other hypotheses; downstream consumers should inspect top-N outcomes, not only one row.
        """
        rules: list[RuleOutcome] = []

        if not snapshot.ping_ip_ok:
            rules.append(
                RuleOutcome(
                    rule_id="ping_fail_path",
                    cause="Local link, router, ISP path, or ICMP blockage",
                    confidence=0.82,
                    explanation=(
                        "ICMP to a public IP failed while other layers were not fully evaluated. "
                        "This pattern usually indicates cabling/Wi-Fi, adapter power saving, "
                        "gateway/router fault, ISP outage, or ICMP filtering."
                    ),
                    recommended_next_action=(
                        "Verify physical link and gateway reachability; reboot router; "
                        "try alternate network; check adapter driver and power management."
                    ),
                )
            )

        if snapshot.ping_ip_ok and not snapshot.nslookup_ok:
            rules.append(
                RuleOutcome(
                    rule_id="dns_failure_likely",
                    cause="DNS resolution failure",
                    confidence=0.88,
                    explanation=(
                        "IP-layer reachability succeeded but name resolution failed—consistent "
                        "with bad DNS servers, stale resolver cache, or captive portal/DNS hijack."
                    ),
                    recommended_next_action=(
                        "Flush DNS cache and validate configured DNS servers; try explicit "
                        "DNS (e.g., operator-provided resolvers); review VPN/split-tunnel settings."
                    ),
                )
            )

        if snapshot.ping_ip_ok and snapshot.nslookup_ok and not snapshot.curl_https_ok:
            rules.append(
                RuleOutcome(
                    rule_id="https_path_failure",
                    cause="HTTPS/application-path failure (proxy, TLS, filter, or browser stack)",
                    confidence=0.85,
                    explanation=(
                        "Ping and DNS succeeded but HTTPS fetch failed—often proxy/TLS inspection, "
                        "local firewall filtering HTTPS, AV HTTPS scanning, or WinHTTP/WinINET mismatch."
                    ),
                    recommended_next_action=(
                        "Inspect WinHTTP and user proxy settings; test with another client; "
                        "review TLS errors from curl output; validate firewall/AV HTTPS scanning."
                    ),
                )
            )

        if snapshot.proxy_server_line_present or (
            not snapshot.winhttp_direct and snapshot.ping_ip_ok
        ):
            rules.append(
                RuleOutcome(
                    rule_id="proxy_misconfiguration",
                    cause="Proxy misconfiguration or unintended proxy usage",
                    confidence=0.78,
                    explanation=(
                        "WinHTTP indicates a proxy server or non-direct path while baseline "
                        "expectation for many home networks is direct access."
                    ),
                    recommended_next_action=(
                        "Review PAC/auto-config vs manual proxy; align WinHTTP with intended policy; "
                        "clear stale proxy after VPN disconnect using toolkit guidance."
                    ),
                )
            )

        if snapshot.intermittent_reported:
            rules.append(
                RuleOutcome(
                    rule_id="intermittent_instability",
                    cause="Intermittent connectivity or unstable resolver/path",
                    confidence=0.62,
                    explanation=(
                        "Operator reported intermittent symptoms—consistent with Wi-Fi noise, "
                        "DHCP/DNS churn, router instability, driver bugs, or upstream ISP variance."
                    ),
                    recommended_next_action=(
                        "Collect time-stamped snapshots; monitor DNS/proxy transitions; "
                        "update NIC drivers; try wired link; review router firmware and thermal."
                    ),
                )
            )

        # Healthy baseline hint (low salience)
        if (
            snapshot.ping_ip_ok
            and snapshot.nslookup_ok
            and snapshot.curl_https_ok
            and snapshot.winhttp_direct
            and not snapshot.intermittent_reported
        ):
            rules.append(
                RuleOutcome(
                    rule_id="baseline_ok",
                    cause="No strong failure signature in this snapshot",
                    confidence=0.35,
                    explanation=(
                        "Core probes succeeded with direct WinHTTP—symptoms may be application-specific, "
                        "intermittent, or outside this probe set."
                    ),
                    recommended_next_action=(
                        "If issues persist, rerun with intermittent flag; capture browser-specific errors; "
                        "use toolkit browser/proxy deep probes."
                    ),
                )
            )

        rules.sort(key=lambda r: r.confidence, reverse=True)
        return rules

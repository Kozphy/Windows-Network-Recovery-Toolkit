"""Rule-based remediation planner for local agent workflows.

This module maps primary root-cause hypotheses into minimal repair plans.
It sits between classification and execution layers, enforcing conservative
defaults that avoid automatic high-risk actions.

Key invariants:
    - Planner returns deterministic plans for identical inputs.
    - Firewall reset step can be suggested but requires explicit executor opt-in.
    - Unknown diagnoses default to read-only evidence collection.
"""

from __future__ import annotations

from .schemas import DiagnosticEvidence, RankedCause, RepairPlan, RepairStep, RiskLevel, RootCauseCategory


def _step(
    script: str,
    description: str,
    risk: RiskLevel,
    *,
    requires_confirmation: bool,
    destructive: bool,
) -> RepairStep:
    """Create a normalized repair step entry.

    Args:
        script: Repository-relative script path.
        description: Human-readable action description.
        risk: Risk classification label.
        requires_confirmation: Whether caller must explicitly confirm execution.
        destructive: Whether action can significantly mutate host state.

    Returns:
        RepairStep: Immutable step object for planning/execution.
    """
    return RepairStep(
        script_relative_path=script,
        description=description,
        risk=risk,
        requires_confirmation=requires_confirmation,
        destructive=destructive,
    )


def plan(primary: RankedCause | None, _evidence: DiagnosticEvidence) -> RepairPlan:
    """Build a repair plan from the selected root-cause hypothesis.

    Decision intent:
        Prefer the smallest safe corrective action first and escalate only when
        evidence indicates broader stack issues.

    Input assumptions:
        - `primary` is the best-ranked cause from classifier output.
        - `_evidence` is provided for future extensibility (currently not used
          to branch within this planner).

    Output guarantees:
        - Always returns a `RepairPlan` with rationale and verification hint.
        - Plan may contain zero executable steps for manual-only categories.

    Side effects:
        None.

    Idempotency:
        Fully idempotent for identical inputs.

    Constraints and limitations:
        - Planner does not dynamically inspect script presence at plan time.
        - Confidence thresholds are handled upstream in classification.

    Audit Notes:
        - What can go wrong: wrong primary hypothesis produces suboptimal plan.
        - Detection: compare plan rationale to collected evidence.
        - Recovery: rerun diagnostics, inspect ranked causes, choose safer step.

    Args:
        primary: Primary ranked cause or `None` when classifier yielded no cause.
        _evidence: Current diagnostic evidence snapshot.

    Returns:
        RepairPlan: Ordered candidate actions and verification guidance.
    """
    cat: RootCauseCategory = primary.category if primary else "unknown"

    # dns_issue
    if cat == "dns_issue":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\reset_dns.bat",
                    "Flush DNS cache and display resolver configuration.",
                    "LOW",
                    requires_confirmation=False,
                    destructive=False,
                ),
            ),
            rationale="DNS resolution failed while basic IP reachability succeeded.",
            verification_hint="Re-run nslookup and HTTPS HEAD checks.",
        )

    if cat == "proxy_issue":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\reset_proxy.bat",
                    "Clear WinHTTP and user-level proxy settings.",
                    "LOW",
                    requires_confirmation=False,
                    destructive=False,
                ),
            ),
            rationale="Proxy signals correlate with HTTPS failure.",
            verification_hint="Re-check HTTPS and browser proxy settings.",
        )

    if cat == "connection_exhaustion":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\check_connection_exhaustion.bat",
                    "Read-only exhaustion diagnostics (no stack mutation).",
                    "LOW",
                    requires_confirmation=False,
                    destructive=False,
                ),
            ),
            rationale="High TIME_WAIT / ESTABLISHED counts suggest port pressure or leaks.",
            verification_hint=(
                "Restart heavy apps and monitor TIME_WAIT; developer scripts should reuse connections."
            ),
        )

    if cat == "tls_cert_issue":
        return RepairPlan(
            steps=(),
            rationale=(
                "Likely certificate trust or clock skew — automated scripts avoid CA mutation; "
                "review system time and enterprise roots manually."
            ),
            verification_hint="Verify OS clock and inspect TLS errors with curl -v.",
        )

    if cat == "https_issue":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\auto_diagnose.bat",
                    "Read-only diagnosis bundle before invasive repairs.",
                    "LOW",
                    requires_confirmation=False,
                    destructive=False,
                ),
            ),
            rationale="HTTPS path impaired without pure TLS signature — confirm filters/VPN/AV.",
            verification_hint="Retry HTTPS after disabling SSL inspection temporarily for testing.",
        )

    if cat == "tcp_issue":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\check_network.bat",
                    "Layered connectivity evidence without stack reset.",
                    "LOW",
                    requires_confirmation=False,
                    destructive=False,
                ),
                _step(
                    r"scripts\one_click_fix.bat",
                    "Full Winsock/TCP/IP/DNS/proxy reset — disruptive.",
                    "HIGH",
                    requires_confirmation=True,
                    destructive=True,
                ),
            ),
            rationale="Reachability or TCP 443 failures suggest link or stack issues — escalate carefully.",
            verification_hint="Ping/DNS/TCP 443 after repair.",
        )

    if cat == "winsock_issue":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\one_click_fix.bat",
                    "Repair Winsock, TCP/IP stack, DNS cache, and proxies.",
                    "HIGH",
                    requires_confirmation=True,
                    destructive=True,
                ),
            ),
            rationale="Multiple layers failed together — broad repair only after confirmation.",
            verification_hint="Full connectivity sweep post-reboot.",
        )

    if cat == "firewall_issue":
        return RepairPlan(
            steps=(
                _step(
                    r"scripts\reset_firewall.bat",
                    "Firewall reset — NEVER run automatically via agent executor.",
                    "HIGH",
                    requires_confirmation=True,
                    destructive=True,
                ),
            ),
            rationale=(
                "Firewall hypothesis requires explicit human approval; executor blocks without "
                "--confirm-firewall and never chains firewall reset silently."
            ),
            verification_hint="Verify inbound/outbound rules match expectation after manual repair.",
        )

    # unknown / fallback
    return RepairPlan(
        steps=(
            _step(
                r"scripts\auto_diagnose.bat",
                "Collect structured evidence first.",
                "LOW",
                requires_confirmation=False,
                destructive=False,
            ),
        ),
        rationale="Insufficient specificity — prefer observation before repair.",
        verification_hint="Compare diagnostics before and after any manual change.",
    )

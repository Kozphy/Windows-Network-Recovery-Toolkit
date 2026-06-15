"""CLI facade for URL evidence diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.platform_core.url_diagnostics import run_url_diagnose


def diagnose_url(
    url: str,
    *,
    domain_profile: str = "generic",
    follow_redirects: bool = True,
    max_redirects: int = 10,
    compare_browser: bool = False,
    user_agent: str = "",
    timeout: float = 10.0,
    no_body: bool = False,
    classify_soft_404: bool = True,
    save_evidence: bool = False,
    evidence_dir: str = "./evidence",
    run: Callable[..., Any] | None = None,
    inject: dict[str, Any] | None = None,
    body_text: str = "",
) -> dict[str, Any]:
    report = run_url_diagnose(
        url,
        domain_profile=domain_profile,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects,
        compare_browser=compare_browser,
        user_agent=user_agent,
        timeout=timeout,
        no_body=no_body,
        classify_soft_404=classify_soft_404,
        save_evidence=save_evidence,
        evidence_dir=evidence_dir,
        run=run,
        inject=inject,
        body_text=body_text,
    )
    return report.to_dict()


def explain_report(report: dict[str, Any]) -> str:
    """Human-readable summary for --explain."""
    cls = report.get("classification", {})
    risk = report.get("risk_assessment", {})
    decision = report.get("decision", {})
    lines = [
        "URL Evidence Diagnostic",
        "=======================",
        f"URL: {report.get('input', {}).get('url', '')}",
        f"Primary: {cls.get('primary')} (confidence {cls.get('confidence')})",
        f"Secondary: {', '.join(cls.get('secondary') or []) or 'none'}",
        f"Network reachable: {cls.get('network_reachable')}",
        f"Resource reachable: {cls.get('resource_reachable')}",
        f"Severity: {risk.get('severity')}",
        f"User impact: {risk.get('user_impact')}",
        f"Safe to auto-fix network: {decision.get('safe_to_auto_fix_network')}",
        f"Reason: {decision.get('reason')}",
        "",
        "Recommended next steps:",
    ]
    for step in report.get("recommended_next_steps", []):
        lines.append(f"  - {step}")
    for lim in report.get("limitations", []):
        lines.append(f"  [{lim}]")
    return "\n".join(lines)

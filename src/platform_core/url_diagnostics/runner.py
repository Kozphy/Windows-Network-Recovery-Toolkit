"""URL diagnostic orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .browser_compare import compare_browser_paths
from .classifier import classify_url_failure
from .dns_probe import probe_dns
from .domain_profiles import get_profile
from .evidence_writer import write_evidence
from .http_probe import probe_http
from .models import (
    AuditBlock,
    DecisionBlock,
    HttpObservation,
    ProbeStatus,
    RedirectObservation,
    RiskAssessmentBlock,
    Soft404Observation,
    TcpObservation,
    TlsObservation,
    UrlDiagnosticClassification,
    UrlDiagnosticInput,
    UrlDiagnosticReport,
)
from .recommendations import (
    build_decision,
    build_recommendations,
    build_risk_assessment,
    default_limitations,
)
from .redirect_analyzer import analyze_redirects
from .soft404_detector import detect_soft404
from .tcp_probe import probe_tcp
from .tls_probe import probe_tls


def run_url_diagnose(
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
) -> UrlDiagnosticReport:
    """Run read-only URL evidence diagnostic; inject overrides probes for tests."""
    diag_input = UrlDiagnosticInput(
        url=url,
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
    )
    profile = get_profile(domain_profile)
    inj = inject or {}

    dns = probe_dns(url, timeout=timeout, inject=inj.get("dns"))

    if inj.get("tcp") is not None:
        tcp = probe_tcp(url, timeout=timeout, inject=inj.get("tcp"))
    elif dns.status != ProbeStatus.OK:
        tcp = TcpObservation(status=ProbeStatus.SKIPPED, error="skipped_after_dns_failure")
    else:
        tcp = probe_tcp(url, timeout=timeout, inject=None)

    if inj.get("tls") is not None:
        tls = probe_tls(url, timeout=timeout, inject=inj.get("tls"))
    elif tcp.status != ProbeStatus.OK:
        tls = TlsObservation(status=ProbeStatus.SKIPPED, error="skipped_after_tcp_failure")
    else:
        tls = probe_tls(url, timeout=timeout, inject=None)

    if inj.get("http") is not None:
        http = probe_http(
            url,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            user_agent=user_agent,
            timeout=timeout,
            no_body=no_body,
            inject=inj.get("http"),
        )
    elif tls.status == ProbeStatus.FAIL:
        http = HttpObservation(status=ProbeStatus.SKIPPED, error="skipped_after_tls_failure")
    else:
        http = probe_http(
            url,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            user_agent=user_agent,
            timeout=timeout,
            no_body=no_body,
            inject=None,
        )

    redirect = analyze_redirects(
        url,
        http,
        profile=profile,
        max_redirects=max_redirects,
    )
    if inj.get("redirect"):
        redirect = RedirectObservation.model_validate(inj["redirect"])

    soft404 = detect_soft404(
        url,
        http,
        profile=profile,
        classify_soft_404=classify_soft_404,
        body_text=body_text or inj.get("body_text", ""),
    )
    if inj.get("soft404"):
        soft404 = Soft404Observation.model_validate(inj["soft404"])

    browser = None
    if compare_browser or inj.get("browser_compare"):
        browser = compare_browser_paths(
            url,
            http,
            run=run,
            timeout=timeout,
            inject=inj.get("browser_compare"),
            browser_ua_result=inj.get("browser_ua_result"),
        )

    classification = classify_url_failure(
        dns=dns,
        tcp=tcp,
        tls=tls,
        http=http,
        redirect=redirect,
        soft404=soft404,
        profile=profile,
        browser=browser,
    )
    if inj.get("classification"):
        classification = UrlDiagnosticClassification.model_validate(inj["classification"])

    risk_dict = build_risk_assessment(classification)
    decision_dict = build_decision(classification)
    steps = build_recommendations(classification, domain_profile=domain_profile, url=url)

    observations = {
        "dns": dns.model_dump(mode="json"),
        "tcp": tcp.model_dump(mode="json"),
        "tls": tls.model_dump(mode="json"),
        "http": http.model_dump(mode="json"),
        "redirect": redirect.model_dump(mode="json"),
        "soft404": soft404.model_dump(mode="json"),
    }

    report = UrlDiagnosticReport(
        input=diag_input,
        observations=observations,
        classification=classification,
        risk_assessment=RiskAssessmentBlock.model_validate(risk_dict),
        recommended_next_steps=steps,
        decision=DecisionBlock.model_validate(decision_dict),
        audit=AuditBlock(),
        limitations=default_limitations(),
        browser_compare=browser,
    )

    if save_evidence:
        payload = report.to_dict()
        files = write_evidence(
            payload,
            evidence_dir=evidence_dir,
            body_excerpt=body_text or inj.get("body_text", ""),
        )
        report.audit.evidence_files = files

    return report

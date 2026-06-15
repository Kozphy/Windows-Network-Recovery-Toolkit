"""Classify URL failures by network vs application layer."""

from __future__ import annotations

from .domain_profiles import DomainProfile
from .models import (
    BrowserCompareObservation,
    ClassificationPrimary,
    ClassificationSecondary,
    DnsObservation,
    HttpObservation,
    ProbeStatus,
    RedirectObservation,
    Soft404Observation,
    TcpObservation,
    TlsObservation,
    UrlDiagnosticClassification,
)


def _network_ok(
    dns: DnsObservation,
    tcp: TcpObservation,
    tls: TlsObservation,
    http: HttpObservation,
) -> bool:
    if dns.status != ProbeStatus.OK:
        return False
    if tcp.status != ProbeStatus.OK:
        return False
    if tls.status not in {ProbeStatus.OK, ProbeStatus.SKIPPED}:
        return False
    return http.status == ProbeStatus.OK


def classify_url_failure(
    *,
    dns: DnsObservation,
    tcp: TcpObservation,
    tls: TlsObservation,
    http: HttpObservation,
    redirect: RedirectObservation,
    soft404: Soft404Observation,
    profile: DomainProfile,
    browser: BrowserCompareObservation | None = None,
) -> UrlDiagnosticClassification:
    secondary: list[str] = []

    if dns.status != ProbeStatus.OK:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.DNS_FAILURE,
            network_reachable=False,
            resource_reachable=False,
            confidence=0.88,
        )

    if tcp.status != ProbeStatus.OK:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.TCP_CONNECT_FAILURE,
            network_reachable=False,
            resource_reachable=False,
            confidence=0.86,
        )

    if http.proxy_error or (browser and _proxy_mismatch(browser)):
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.PROXY_FAILURE,
            secondary=_proxy_secondary(browser),
            network_reachable=False,
            resource_reachable=False,
            confidence=0.84,
        )

    if tls.status == ProbeStatus.FAIL:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.TLS_FAILURE,
            network_reachable=False,
            resource_reachable=False,
            confidence=0.87,
        )

    if http.status != ProbeStatus.OK:
        if redirect.loop_detected:
            return UrlDiagnosticClassification(
                primary=ClassificationPrimary.REDIRECT_LOOP_OR_CHAIN_FAILURE,
                network_reachable=_partial_network(dns, tcp, tls),
                resource_reachable=False,
                confidence=0.80,
            )
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.UNKNOWN_APPLICATION_LAYER_FAILURE,
            network_reachable=_partial_network(dns, tcp, tls),
            resource_reachable=False,
            confidence=0.55,
        )

    code = http.status_code or 0
    net_ok = _network_ok(dns, tcp, tls, http)

    if redirect.loop_detected:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.REDIRECT_LOOP_OR_CHAIN_FAILURE,
            secondary=_redirect_secondary(redirect, secondary),
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.85,
        )

    if redirect.suspicious_shortlink and redirect.hop_count == 0 and code >= 400:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.TRACKING_SHORTLINK_ISSUE,
            secondary=[ClassificationSecondary.SHORTLINK_EXPANDED.value],
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.72,
        )

    if code in {500, 502, 503, 504}:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.REMOTE_SERVER_ERROR,
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.82,
        )

    if code == 403:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.PERMISSION_OR_ACCESS_DENIED,
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.88,
        )

    if code == 410:
        secondary = _linkedin_secondary(profile, soft404, secondary)
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.APPLICATION_RESOURCE_NOT_FOUND,
            secondary=secondary,
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.90 if soft404.detected else 0.85,
        )

    if code == 404:
        secondary = _linkedin_secondary(profile, soft404, secondary)
        if soft404.detected and profile.name == "linkedin":
            secondary.append(ClassificationSecondary.LINKEDIN_SOFT_404.value)
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.APPLICATION_RESOURCE_NOT_FOUND,
            secondary=secondary,
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.92 if soft404.detected else 0.86,
        )

    if http.login_signals or _login_wall(http, profile):
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.LOGIN_REQUIRED,
            secondary=[ClassificationSecondary.LOGIN_WALL.value],
            network_reachable=net_ok,
            resource_reachable=True,
            confidence=0.78,
        )

    if code == 200 and soft404.detected:
        secondary = _linkedin_secondary(profile, soft404, secondary)
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.SOFT_404_OR_CONTENT_NOT_FOUND,
            secondary=secondary,
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.90,
        )

    if _regional_signal(http, profile):
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.REGIONAL_ACCOUNT_VISIBILITY,
            network_reachable=net_ok,
            resource_reachable=False,
            confidence=0.70,
        )

    if redirect.domain_changed:
        secondary.append(ClassificationSecondary.REDIRECT_DOMAIN_CHANGE.value)

    if redirect.suspicious_shortlink and redirect.hop_count > 0:
        secondary.append(ClassificationSecondary.SHORTLINK_EXPANDED.value)

    if code == 200 and net_ok:
        return UrlDiagnosticClassification(
            primary=ClassificationPrimary.UNKNOWN_APPLICATION_LAYER_FAILURE,
            secondary=secondary,
            network_reachable=True,
            resource_reachable=True,
            confidence=0.60,
        )

    return UrlDiagnosticClassification(
        primary=ClassificationPrimary.UNKNOWN_APPLICATION_LAYER_FAILURE,
        secondary=secondary,
        network_reachable=net_ok,
        resource_reachable=code < 400,
        confidence=0.55,
    )


def _partial_network(dns: DnsObservation, tcp: TcpObservation, tls: TlsObservation) -> bool:
    return (
        dns.status == ProbeStatus.OK
        and tcp.status == ProbeStatus.OK
        and tls.status in {ProbeStatus.OK, ProbeStatus.SKIPPED}
    )


def _proxy_mismatch(browser: BrowserCompareObservation) -> bool:
    return bool(browser.mismatches)


def _proxy_secondary(browser: BrowserCompareObservation | None) -> list[str]:
    if browser and browser.mismatches:
        return list(browser.mismatches[:3])
    return []


def _redirect_secondary(redirect: RedirectObservation, secondary: list[str]) -> list[str]:
    out = list(secondary)
    if redirect.domain_changed:
        out.append(ClassificationSecondary.REDIRECT_DOMAIN_CHANGE.value)
    if redirect.suspicious_shortlink:
        out.append(ClassificationSecondary.SHORTLINK_EXPANDED.value)
    return out


def _linkedin_secondary(
    profile: DomainProfile,
    soft404: Soft404Observation,
    secondary: list[str],
) -> list[str]:
    out = list(secondary)
    if profile.name == "linkedin" and soft404.detected:
        tag = ClassificationSecondary.LINKEDIN_SOFT_404.value
        if tag not in out:
            out.append(tag)
    return out


def _login_wall(http: HttpObservation, profile: DomainProfile) -> bool:
    combined = f"{http.title} {http.final_url}".lower()
    return profile.name == "linkedin" and "authwall" in combined


def _regional_signal(http: HttpObservation, profile: DomainProfile) -> bool:
    text = http.title.lower()
    return any(p.search(text) for p in profile.regional_signals)

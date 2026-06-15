"""Recommended next steps for URL diagnostic outcomes."""

from __future__ import annotations

from .models import ClassificationPrimary, ClassificationSecondary, UrlDiagnosticClassification

_BASE_LIMITATIONS = [
    "Observation is not proof.",
    "Correlation is not causation.",
    "Confidence is not certainty.",
    "Policy permission is not a safety guarantee.",
]


def build_recommendations(
    classification: UrlDiagnosticClassification,
    *,
    domain_profile: str,
    url: str,
) -> list[str]:
    primary = classification.primary
    steps: list[str] = []

    if primary == ClassificationPrimary.DNS_FAILURE:
        steps.extend([
            "Verify DNS resolver settings (ipconfig /all, nslookup).",
            "Try an alternate network or DNS server.",
            "Check corporate VPN or split-tunnel DNS policies.",
        ])
    elif primary == ClassificationPrimary.TCP_CONNECT_FAILURE:
        steps.extend([
            "Confirm firewall and proxy settings allow outbound HTTPS.",
            "Test connectivity with Test-NetConnection or ping/traceroute.",
            "Check whether a VPN or captive portal is blocking the path.",
        ])
    elif primary == ClassificationPrimary.PROXY_FAILURE:
        steps.extend([
            "Run proxy-status to inspect WinINET/WinHTTP configuration.",
            "Compare direct vs system-proxy HTTP paths.",
            "Preview proxy remediation only after human confirmation.",
        ])
    elif primary == ClassificationPrimary.TLS_FAILURE:
        steps.extend([
            "Inspect certificate trust store and TLS interception tools.",
            "Run tls-proof to contrast direct vs proxied certificate paths.",
            "Check system date/time and corporate TLS inspection policies.",
        ])
    elif primary in {
        ClassificationPrimary.APPLICATION_RESOURCE_NOT_FOUND,
        ClassificationPrimary.SOFT_404_OR_CONTENT_NOT_FOUND,
    }:
        steps.extend(_app_not_found_steps(domain_profile, url))
    elif primary == ClassificationPrimary.PERMISSION_OR_ACCESS_DENIED:
        steps.extend([
            "Verify you are signed in with the correct account.",
            "Check whether the resource is private or restricted to connections.",
            "Try the URL in an incognito/private browser window.",
        ])
    elif primary == ClassificationPrimary.REMOTE_SERVER_ERROR:
        steps.extend([
            "Retry after a short interval — remote server may be degraded.",
            "Check vendor status pages for the target service.",
            "Escalate to the application owner if errors persist.",
        ])
    elif primary == ClassificationPrimary.REDIRECT_LOOP_OR_CHAIN_FAILURE:
        steps.extend([
            "Expand and inspect the full redirect chain.",
            "Remove tracking parameters or use the canonical URL.",
            "Try opening the destination domain directly.",
        ])
    elif primary == ClassificationPrimary.LOGIN_REQUIRED:
        steps.extend([
            "Sign in to the target service and retry the URL.",
            "Confirm the account has access to this resource.",
        ])
    elif primary == ClassificationPrimary.TRACKING_SHORTLINK_ISSUE:
        steps.extend([
            "Expand the shortlink manually and retry the final URL.",
            "Verify the shortlink has not expired.",
        ])
    elif primary == ClassificationPrimary.REGIONAL_ACCOUNT_VISIBILITY:
        steps.extend([
            "Check regional or account visibility restrictions.",
            "Try from an approved geography or corporate network.",
        ])
    else:
        steps.append("Collect additional evidence before changing network settings.")

    return steps


def _app_not_found_steps(domain_profile: str, url: str) -> list[str]:
    steps = [
        "Check whether the URL was copied completely.",
        "Try opening the same URL in an incognito browser.",
        "If it is a redirect or shortlink, expand the redirect chain.",
    ]
    if domain_profile == "linkedin":
        steps.extend([
            "Open linkedin.com/feed to verify account access.",
            "Try the URL while logged in.",
            "If it is a job or post URL, check whether it expired or was deleted.",
        ])
    else:
        steps.append(f"Verify the resource still exists at {url[:80]}.")
    return steps


def build_risk_assessment(classification: UrlDiagnosticClassification) -> dict[str, object]:
    primary = classification.primary
    app_layer = primary in {
        ClassificationPrimary.APPLICATION_RESOURCE_NOT_FOUND,
        ClassificationPrimary.SOFT_404_OR_CONTENT_NOT_FOUND,
        ClassificationPrimary.PERMISSION_OR_ACCESS_DENIED,
        ClassificationPrimary.LOGIN_REQUIRED,
        ClassificationPrimary.REGIONAL_ACCOUNT_VISIBILITY,
    }

    if app_layer and classification.network_reachable:
        return {
            "severity": "LOW",
            "user_impact": (
                "Specific URL cannot be opened, but general network appears functional."
            ),
            "not_evidence_of": [
                "DNS outage",
                "TLS MITM",
                "WinINET proxy drift",
                "general LinkedIn outage"
                if ClassificationSecondary.LINKEDIN_SOFT_404.value in classification.secondary
                else "general site outage",
            ],
        }

    if primary in {ClassificationPrimary.DNS_FAILURE, ClassificationPrimary.TCP_CONNECT_FAILURE}:
        return {
            "severity": "HIGH",
            "user_impact": "Lower-layer connectivity failure may affect many destinations.",
            "not_evidence_of": [],
        }

    if primary == ClassificationPrimary.PROXY_FAILURE:
        return {
            "severity": "MEDIUM",
            "user_impact": "Proxy path failure may explain browser errors for HTTPS sites.",
            "not_evidence_of": ["application-layer 404"],
        }

    return {
        "severity": "MEDIUM",
        "user_impact": "Further investigation recommended before network remediation.",
        "not_evidence_of": [],
    }


def build_decision(classification: UrlDiagnosticClassification) -> dict[str, object]:
    app_layer = classification.primary in {
        ClassificationPrimary.APPLICATION_RESOURCE_NOT_FOUND,
        ClassificationPrimary.SOFT_404_OR_CONTENT_NOT_FOUND,
        ClassificationPrimary.PERMISSION_OR_ACCESS_DENIED,
        ClassificationPrimary.LOGIN_REQUIRED,
        ClassificationPrimary.REGIONAL_ACCOUNT_VISIBILITY,
        ClassificationPrimary.TRACKING_SHORTLINK_ISSUE,
    }
    if app_layer and classification.network_reachable:
        return {
            "safe_to_auto_fix_network": False,
            "reason": (
                "HTTP content was successfully received from the remote service, "
                "so this is not proven to be a local network configuration failure."
            ),
        }
    if classification.primary == ClassificationPrimary.PROXY_FAILURE:
        return {
            "safe_to_auto_fix_network": False,
            "reason": "Proxy remediation requires explicit policy confirmation and preview.",
        }
    return {
        "safe_to_auto_fix_network": False,
        "reason": "No automatic network remediation without proof envelope and confirmation.",
    }


def default_limitations() -> list[str]:
    return list(_BASE_LIMITATIONS)

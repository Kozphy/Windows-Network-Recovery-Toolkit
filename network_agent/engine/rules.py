from __future__ import annotations

"""Shared decision constants for issue labels and safe action mapping.

This module defines canonical taxonomy values used across the decision engine,
API responses, and report payloads. It sits between decision scoring and serving
layers to ensure stable, audit-friendly identifiers.

Key invariants:
- Issue labels are immutable public contract strings.
- Every supported issue maps to exactly one recommended action key.
- No runtime side effects; module is import-safe and deterministic.
"""

ISSUE_DNS_FAILURE = "DNS_FAILURE"
ISSUE_PROXY_MISCONFIG = "PROXY_MISCONFIGURATION"
ISSUE_TCP_CONNECTIVITY = "TCP_CONNECTIVITY_ISSUE"
ISSUE_HTTPS_CERT = "HTTPS_CERTIFICATE_ISSUE"
ISSUE_FIREWALL_BLOCK = "FIREWALL_LIKELY_BLOCKING"
ISSUE_WINSOCK_CORRUPTION = "WINSOCK_CORRUPTION_SUSPECTED"

ALL_ISSUES = (
    ISSUE_DNS_FAILURE,
    ISSUE_PROXY_MISCONFIG,
    ISSUE_TCP_CONNECTIVITY,
    ISSUE_HTTPS_CERT,
    ISSUE_FIREWALL_BLOCK,
    ISSUE_WINSOCK_CORRUPTION,
)

RECOMMENDED_ACTIONS = {
    ISSUE_DNS_FAILURE: "flush_dns_cache",
    ISSUE_PROXY_MISCONFIG: "reset_proxy_settings",
    ISSUE_TCP_CONNECTIVITY: "renew_ip_and_check_gateway",
    ISSUE_HTTPS_CERT: "review_certificate_chain_and_ssl_inspection",
    ISSUE_FIREWALL_BLOCK: "review_firewall_rules_manually",
    ISSUE_WINSOCK_CORRUPTION: "winsock_reset_preview",
}

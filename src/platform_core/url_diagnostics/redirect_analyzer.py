"""Redirect chain analysis."""

from __future__ import annotations

from urllib.parse import urlparse

from .domain_profiles import DomainProfile, is_shortlink_host
from .models import HttpObservation, RedirectObservation


def analyze_redirects(
    original_url: str,
    http: HttpObservation,
    *,
    profile: DomainProfile,
    max_redirects: int = 10,
) -> RedirectObservation:
    chain = http.redirect_chain or [original_url]
    hops = len(chain) - 1 if len(chain) > 1 else len(http.redirect_hops)

    original_domain = (urlparse(original_url).hostname or "").lower()
    final_domain = (urlparse(http.final_url or original_url).hostname or "").lower()
    domain_changed = bool(original_domain and final_domain and original_domain != final_domain)

    seen: set[str] = set()
    loop_detected = False
    for u in chain:
        if u in seen:
            loop_detected = True
            break
        seen.add(u)

    if hops > max_redirects:
        loop_detected = True

    suspicious = is_shortlink_host(original_url, profile)
    expanded = http.final_url if suspicious and http.final_url else ""

    return RedirectObservation(
        hop_count=hops,
        loop_detected=loop_detected,
        domain_changed=domain_changed,
        original_domain=original_domain,
        final_domain=final_domain,
        suspicious_shortlink=suspicious,
        expanded_url=expanded,
    )

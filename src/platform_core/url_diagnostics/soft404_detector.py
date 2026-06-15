"""Soft-404 and login-wall signal detection."""

from __future__ import annotations

import re

from .domain_profiles import DomainProfile, path_matches_profile
from .models import HttpObservation, Soft404Observation


def _signal_id(pattern: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", pattern.lower()).strip("_")
    return slug[:80]


def detect_soft404(
    url: str,
    http: HttpObservation,
    *,
    profile: DomainProfile,
    classify_soft_404: bool = True,
    body_text: str = "",
) -> Soft404Observation:
    if not classify_soft_404:
        return Soft404Observation(profile=profile.name)

    title = http.title or ""
    body = body_text
    signals: list[str] = []

    for pat in profile.soft_404_title_patterns:
        if pat.search(title):
            signals.append(f"title_matches_{_signal_id(pat.pattern)}")

    for pat in profile.soft_404_body_patterns:
        if pat.search(body) or pat.search(title):
            sig = f"page_text_contains_{_signal_id(pat.pattern)}"
            if sig not in signals:
                signals.append(sig)

    if profile.name == "linkedin" and http.status_code in {404, 410}:
        signals.append("linkedin_not_found_template_detected")

    if path_matches_profile(url, profile) and http.status_code in {404, 410, 200}:
        if "page_text_contains_this_page_doesnt_exist" not in signals:
            if re.search(r"this page doesn.t exist", f"{title} {body}", re.I):
                signals.append("page_text_contains_this_page_doesnt_exist")

    login_signals: list[str] = []
    for pat in profile.login_body_patterns:
        if pat.search(body) or pat.search(title):
            login_signals.append(f"login_signal_{_signal_id(pat.pattern)}")

    http.soft_404_signals = signals
    http.login_signals = login_signals

    return Soft404Observation(
        detected=bool(signals),
        signals=signals,
        profile=profile.name,
    )

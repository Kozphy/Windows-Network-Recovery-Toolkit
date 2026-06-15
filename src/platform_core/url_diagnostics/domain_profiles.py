"""Domain-specific URL path and soft-404 signal profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class DomainProfile:
    name: str
    path_patterns: tuple[re.Pattern[str], ...] = ()
    soft_404_title_patterns: tuple[re.Pattern[str], ...] = ()
    soft_404_body_patterns: tuple[re.Pattern[str], ...] = ()
    login_body_patterns: tuple[re.Pattern[str], ...] = ()
    shortlink_hosts: frozenset[str] = frozenset()
    regional_signals: tuple[re.Pattern[str], ...] = ()


_LINKEDIN_PATHS = (
    r"/in/",
    r"/posts/",
    r"/jobs/view/",
    r"/learning/",
    r"/feed/update/",
    r"/company/",
    r"/pulse/",
)

LINKEDIN_PROFILE = DomainProfile(
    name="linkedin",
    path_patterns=tuple(re.compile(p, re.I) for p in _LINKEDIN_PATHS),
    soft_404_title_patterns=(
        re.compile(r"this page doesn.t exist", re.I),
        re.compile(r"page not found", re.I),
    ),
    soft_404_body_patterns=(
        re.compile(r"this page doesn.t exist", re.I),
        re.compile(r"please check your url or return to linkedin home", re.I),
        re.compile(r"go to your feed", re.I),
        re.compile(r"linkedin_not_found_template", re.I),
    ),
    login_body_patterns=(
        re.compile(r"sign in to linkedin", re.I),
        re.compile(r"join linkedin", re.I),
        re.compile(r"authwall", re.I),
    ),
    shortlink_hosts=frozenset({"lnkd.in", "linked.in"}),
    regional_signals=(
        re.compile(r"not available in your region", re.I),
        re.compile(r"content is not available", re.I),
    ),
)

GENERIC_PROFILE = DomainProfile(
    name="generic",
    soft_404_title_patterns=(
        re.compile(r"not found", re.I),
        re.compile(r"404", re.I),
    ),
    soft_404_body_patterns=(
        re.compile(r"page not found", re.I),
        re.compile(r"doesn.t exist", re.I),
    ),
    login_body_patterns=(
        re.compile(r"sign in", re.I),
        re.compile(r"log in", re.I),
    ),
    shortlink_hosts=frozenset({"bit.ly", "t.co", "goo.gl", "lnkd.in"}),
)

_PROFILES: dict[str, DomainProfile] = {
    "linkedin": LINKEDIN_PROFILE,
    "generic": GENERIC_PROFILE,
}


def get_profile(name: str) -> DomainProfile:
    return _PROFILES.get(name.lower(), GENERIC_PROFILE)


def path_matches_profile(url: str, profile: DomainProfile) -> bool:
    path = urlparse(url).path or "/"
    return any(p.search(path) for p in profile.path_patterns)


def is_shortlink_host(url: str, profile: DomainProfile) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in profile.shortlink_hosts

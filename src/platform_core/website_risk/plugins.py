"""Optional reputation API plugins — no hard-coded API keys."""

from __future__ import annotations

import os
from typing import Any, Protocol

from .models import WebsiteRiskEvidence


class ReputationPlugin(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def lookup(self, url: str) -> list[WebsiteRiskEvidence]: ...


class VirusTotalPlugin:
    name = "virustotal"

    def is_configured(self) -> bool:
        return bool(os.environ.get("VIRUSTOTAL_API_KEY", "").strip())

    def lookup(self, url: str) -> list[WebsiteRiskEvidence]:
        key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
        if not key:
            return []
        return [
            WebsiteRiskEvidence(
                signal="reputation_virustotal",
                observed="not_queried_live_in_tests",
                weight=0.0,
                detail="Configure VIRUSTOTAL_API_KEY to enable live lookups.",
            )
        ]


class GoogleSafeBrowsingPlugin:
    name = "google_safe_browsing"

    def is_configured(self) -> bool:
        return bool(os.environ.get("GOOGLE_SAFEBROWSING_API_KEY", "").strip())

    def lookup(self, url: str) -> list[WebsiteRiskEvidence]:
        if not self.is_configured():
            return []
        return [
            WebsiteRiskEvidence(
                signal="reputation_safe_browsing",
                observed="not_queried_live_in_tests",
                weight=0.0,
                detail="Configure GOOGLE_SAFEBROWSING_API_KEY to enable live lookups.",
            )
        ]


class URLHausPlugin:
    name = "urlhaus"

    def is_configured(self) -> bool:
        return bool(os.environ.get("URLHAUS_API_KEY", "").strip())

    def lookup(self, url: str) -> list[WebsiteRiskEvidence]:
        if not self.is_configured():
            return []
        return []


class PhishTankPlugin:
    name = "phishtank"

    def is_configured(self) -> bool:
        return bool(os.environ.get("PHISHTANK_API_KEY", "").strip())

    def lookup(self, url: str) -> list[WebsiteRiskEvidence]:
        if not self.is_configured():
            return []
        return []


def default_plugins() -> list[ReputationPlugin]:
    return [
        VirusTotalPlugin(),
        GoogleSafeBrowsingPlugin(),
        URLHausPlugin(),
        PhishTankPlugin(),
    ]


def run_reputation_plugins(
    url: str,
    plugins: list[ReputationPlugin] | None = None,
) -> tuple[list[WebsiteRiskEvidence], list[str]]:
    used: list[str] = []
    evidence: list[WebsiteRiskEvidence] = []
    for plugin in plugins or default_plugins():
        if plugin.is_configured():
            used.append(plugin.name)
            evidence.extend(plugin.lookup(url))
    return evidence, used

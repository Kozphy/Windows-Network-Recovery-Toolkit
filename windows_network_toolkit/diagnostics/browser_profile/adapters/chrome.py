"""Google Chrome Chromium adapter."""

from __future__ import annotations

import os
from pathlib import Path

from windows_network_toolkit.diagnostics.browser_profile.adapters.base import BrowserAdapter
from windows_network_toolkit.diagnostics.browser_profile.adapters.chromium import (
    ChromiumProfileMixin,
)
from windows_network_toolkit.diagnostics.browser_profile.models import (
    BrowserExtensionEvidence,
    BrowserNetworkPreferenceEvidence,
    BrowserPolicyEvidence,
    BrowserProfileEvidence,
    BrowserSiteStateEvidence,
)


class ChromeAdapter(ChromiumProfileMixin, BrowserAdapter):
    name = "chrome"
    browser_name = "chrome"
    process_names = ("chrome.exe",)

    def __init__(self) -> None:
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        self.user_data_candidates = (
            local / "Google" / "Chrome" / "User Data",
        )

    def detect_installation(self) -> dict:
        return super().detect_installation()

    def discover_profiles(self) -> list[BrowserProfileEvidence]:
        return super().discover_profiles()

    def collect_profile_metadata(self, profile: BrowserProfileEvidence) -> BrowserProfileEvidence:
        return super().collect_profile_metadata(profile)

    def collect_policy_metadata(self) -> list[BrowserPolicyEvidence]:
        return super().collect_policy_metadata()

    def collect_extension_metadata(self, profile: BrowserProfileEvidence) -> list[BrowserExtensionEvidence]:
        return super().collect_extension_metadata(profile)

    def collect_site_state_metadata(self, domain: str, profile: BrowserProfileEvidence) -> BrowserSiteStateEvidence:
        return super().collect_site_state_metadata(domain, profile)

    def collect_network_preferences(self, profile: BrowserProfileEvidence) -> BrowserNetworkPreferenceEvidence:
        return super().collect_network_preferences(profile)

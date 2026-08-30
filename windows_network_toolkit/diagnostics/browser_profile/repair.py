"""Repair preview — never apply without explicit confirm."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from windows_network_toolkit.diagnostics.browser_profile.adapters.chromium import domain_matches
from windows_network_toolkit.diagnostics.browser_profile.models import BrowserRepairPreview


def domain_from_url(url: str) -> str:
    host = urlparse(url if "://" in url else f"https://{url}").hostname or url
    return host.lower()


def build_repair_preview(
    domain: str,
    *,
    browser: str,
    has_cookies: bool = False,
    has_service_workers: bool = False,
    has_cache: bool = False,
    proxy_extension_ids: list[str] | None = None,
) -> BrowserRepairPreview:
    """Site-scoped cleanup actions as PREVIEW only."""
    d = domain.lower().lstrip(".")
    actions: list[dict[str, Any]] = [
        {
            "id": "delete_domain_cookies",
            "description": f"Delete cookies scoped to {d} only",
            "destructive": True,
            "applies_if": has_cookies,
            "domain_guard": d,
        },
        {
            "id": "delete_domain_cache",
            "description": f"Delete HTTP cache entries associated with {d}",
            "destructive": True,
            "applies_if": has_cache,
        },
        {
            "id": "delete_domain_local_storage",
            "description": f"Delete Local Storage / IndexedDB for {d}",
            "destructive": True,
        },
        {
            "id": "unregister_domain_service_workers",
            "description": f"Unregister service workers for {d}",
            "destructive": True,
            "applies_if": has_service_workers,
        },
        {
            "id": "reset_domain_permissions",
            "description": f"Reset site permissions for {d}",
            "destructive": True,
        },
        {
            "id": "create_clean_test_profile",
            "description": "Create a dedicated toolkit test profile (does not wipe user Default)",
            "destructive": False,
        },
        {
            "id": "reset_secure_dns_to_system",
            "description": "Reset Secure DNS mode to system default in test profile",
            "destructive": False,
        },
    ]
    for ext_id in proxy_extension_ids or []:
        actions.append(
            {
                "id": f"disable_extension_{ext_id}",
                "description": f"Disable extension {ext_id} for testing only",
                "destructive": True,
            }
        )

    return BrowserRepairPreview(
        preview_id=f"brp-{uuid.uuid4().hex[:12]}",
        domain=d,
        browser=browser,
        dry_run=True,
        actions=actions,
        backup_plan="Export non-secret BrowserSiteStateEvidence JSON before apply.",
        requires_confirm_token="BROWSER_SITE_REPAIR_APPLY",
        limitations=[
            "Preview only — no cookies, storage, or extensions were modified.",
            "Never reset the whole browser profile when site-scoped cleanup suffices.",
            f"Domain guard uses matching helper; unrelated domains must not match '{d}'.",
            "Apply requires: wnrt browser-profile repair-apply <preview-id> --confirm BROWSER_SITE_REPAIR_APPLY",
        ],
    )


def assert_domain_guard(target_domain: str, candidate_domain: str) -> bool:
    """Public guard used by tests — site repair must not hit unrelated domains."""
    return domain_matches(candidate_domain, target_domain) or domain_matches(target_domain, candidate_domain)

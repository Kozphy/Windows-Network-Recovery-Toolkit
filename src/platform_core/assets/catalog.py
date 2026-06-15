"""Seed assets for endpoint network risk domain."""

from __future__ import annotations

from src.platform_core.assets.models import Asset
from src.platform_core.enterprise.enums import Criticality

ASSETS: tuple[Asset, ...] = (
    Asset(
        asset_id="AST-EP-001",
        asset_name="Corporate Endpoint",
        asset_type="Endpoint",
        owner="IT Operations",
        classification="confidential",
        criticality=Criticality.HIGH,
    ),
    Asset(
        asset_id="AST-BRW-001",
        asset_name="Enterprise Browser",
        asset_type="Browser",
        owner="End User Computing",
        classification="internal",
        criticality=Criticality.HIGH,
    ),
    Asset(
        asset_id="AST-PRX-001",
        asset_name="WinINET Proxy Configuration",
        asset_type="Proxy Configuration",
        owner="IT Operations",
        classification="internal",
        criticality=Criticality.HIGH,
    ),
    Asset(
        asset_id="AST-REG-001",
        asset_name="Internet Settings Registry",
        asset_type="Registry",
        owner="IT Operations",
        classification="internal",
        criticality=Criticality.HIGH,
    ),
    Asset(
        asset_id="AST-CERT-001",
        asset_name="Certificate Trust Store",
        asset_type="Certificate Store",
        owner="Security",
        classification="confidential",
        criticality=Criticality.CRITICAL,
    ),
    Asset(
        asset_id="AST-DNS-001",
        asset_name="DNS Resolver Configuration",
        asset_type="DNS Configuration",
        owner="Network Operations",
        classification="internal",
        criticality=Criticality.MEDIUM,
    ),
)


def list_assets() -> list[Asset]:
    return list(ASSETS)


def assets_for_fixture(classification: str) -> list[Asset]:
    """Map technical classification to impacted assets."""
    base = [ASSETS[0], ASSETS[1], ASSETS[2], ASSETS[3]]
    if classification in ("TLS_PATH_MISMATCH", "MITM_SUSPECTED"):
        return base + [ASSETS[4]]
    if classification == "DNS_ISSUE":
        return base + [ASSETS[5]]
    return base

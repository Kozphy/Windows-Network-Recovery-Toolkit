"""Asset models for technology risk context."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Asset(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    criticality: str = "high"
    owner: str = "Endpoint Engineering"
    description: str = ""


def asset_for_fixture(fixture: dict[str, Any]) -> Asset:
    override = fixture.get("asset")
    if override:
        return Asset.model_validate(override)
    state = fixture.get("proxy_state") or {}
    server = state.get("wininet_proxy_server") or "WinINET proxy configuration"
    return Asset(
        asset_id="ASSET_WININET_PROXY",
        name="Windows endpoint WinINET proxy settings",
        asset_type="endpoint_configuration",
        criticality="high",
        owner="IT Operations / Endpoint Engineering",
        description=f"HKCU Internet Settings proxy state (observed: {server})",
    )

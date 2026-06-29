"""Shared fixtures for synthetic local scale tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.fleet.ingestion import FleetIngestGateway


@pytest.fixture
def fleet_gateway(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FleetIngestGateway:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setenv("FLEET_MODE", "local")
    return FleetIngestGateway()

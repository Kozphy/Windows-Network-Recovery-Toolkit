"""Pydantic schemas for ERP platform API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from windows_network_toolkit import SERVICE_NAME, __version__


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME
    version: str = __version__
    dry_run_default: bool = True


class StatusResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME
    version: str = __version__
    platform_mode: str = "local_replay"
    safe_mode: bool = True
    remediation_default: str = "dry_run"


class DiagnoseRequest(BaseModel):
    signals: dict[str, Any] = Field(default_factory=dict)
    fixture_path: str | None = None
    incident_id: str | None = None
    dry_run: bool = True


class ReplayRequest(BaseModel):
    fixture_path: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class RemediationConfirmRequest(BaseModel):
    preview_id: str = ""
    confirmation_phrase: str = ""
    dry_run: bool = True

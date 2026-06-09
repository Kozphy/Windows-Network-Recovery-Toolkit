"""FastAPI router — canonical ERP platform routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from windows_network_toolkit import SERVICE_NAME, __version__
from windows_network_toolkit.audit.jsonl_logger import read_audit_tail
from windows_network_toolkit.audit.replay import _incident_type_value
from windows_network_toolkit.pipeline import run_incident_pipeline
from windows_network_toolkit.platform.schemas import (
    DiagnoseRequest,
    HealthResponse,
    RemediationConfirmRequest,
    ReplayRequest,
    StatusResponse,
)
from windows_network_toolkit.platform.store import get_latest, get_timeline, set_latest
from windows_network_toolkit.remediation import preview_proxy_disable  # used by confirm

router = APIRouter(tags=["erp-platform"])

_REPO = Path(__file__).resolve().parents[2]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, version=__version__)


@router.get("/platform/status", response_model=StatusResponse)
def platform_status() -> StatusResponse:
    return StatusResponse()


@router.post("/platform/diagnose")
def platform_diagnose(body: DiagnoseRequest) -> dict[str, Any]:
    if body.fixture_path:
        path = Path(body.fixture_path)
        if not path.is_file():
            path = _REPO / "windows_network_toolkit" / "examples" / body.fixture_path
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"fixture not found: {body.fixture_path}")
        result = run_incident_pipeline(jsonl_path=path, incident_id=body.incident_id, dry_run=body.dry_run)
    else:
        result = run_incident_pipeline(
            signals=body.signals, incident_id=body.incident_id, dry_run=body.dry_run
        )
    set_latest(result)
    return {
        "incident_id": result.bundle.incident_id,
        "timeline": result.timeline,
        "decision": result.decision.model_dump(),
        "policy": result.policy,
        "remediation": result.remediation,
        "dry_run": body.dry_run,
        "version": __version__,
    }


@router.get("/platform/evidence/timeline")
def platform_evidence_timeline() -> dict[str, Any]:
    timeline = get_timeline()
    return {"timeline": timeline, "count": len(timeline), "dry_run": True}


@router.get("/platform/decision/latest")
def platform_decision_latest() -> dict[str, Any]:
    latest = get_latest()
    if not latest:
        return {
            "decision": None,
            "message": "No diagnosis run yet. POST /platform/diagnose or /platform/replay first.",
            "dry_run": True,
        }
    return {"decision": latest.get("decision"), "incident_id": latest.get("incident_id"), "dry_run": True}


@router.get("/platform/audit/logs")
def platform_audit_logs(limit: int = 50) -> dict[str, Any]:
    rows = read_audit_tail(limit=limit)
    return {"logs": rows, "count": len(rows)}


@router.post("/platform/replay")
def platform_replay(body: ReplayRequest) -> dict[str, Any]:
    if body.fixture_path:
        path = Path(body.fixture_path)
        if not path.is_file():
            path = _REPO / "windows_network_toolkit" / "examples" / body.fixture_path
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"fixture not found: {body.fixture_path}")
        from windows_network_toolkit.audit.replay import replay_jsonl

        result = replay_jsonl(path, dry_run=body.dry_run)
        set_latest(result)
        payload = {
            "incident_id": result.bundle.incident_id,
            "timeline": result.timeline,
            "incident_type": _incident_type_value(result.decision),
            "confidence": result.decision.confidence,
            "decision": result.decision.model_dump(),
            "policy": result.policy,
            "remediation": result.remediation,
            "audit": result.audit_record,
        }
    else:
        result = run_incident_pipeline(signals=body.signals, dry_run=body.dry_run)
        set_latest(result)
        payload = {
            "incident_id": result.bundle.incident_id,
            "timeline": result.timeline,
            "incident_type": _incident_type_value(result.decision),
            "confidence": result.decision.confidence,
            "decision": result.decision.model_dump(),
            "policy": result.policy,
            "remediation": result.remediation,
            "audit": result.audit_record,
        }
    return {**payload, "dry_run": body.dry_run, "version": __version__}


@router.post("/platform/remediation/confirm")
def platform_remediation_confirm(body: RemediationConfirmRequest) -> dict[str, Any]:
  # Alias semantics: confirm maps to execute-with-guards; always dry_run unless explicitly disabled
    if body.dry_run:
        preview = preview_proxy_disable(dry_run=True)
        return {
            "result": "preview_only",
            "preview": preview,
            "preview_id": body.preview_id or "erp-preview",
            "confirmation_required": True,
            "dry_run": True,
            "message": "Live execution blocked in safe mode. Use platform_core remediation execute with typed phrase.",
        }
    return {
        "result": "blocked",
        "dry_run": True,
        "message": "Destructive execution requires platform_core remediation execute path with admin + confirmation.",
    }

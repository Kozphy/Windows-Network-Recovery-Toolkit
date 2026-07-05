"""MCP tool implementations — read-only, auditable."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.platform_core.events import TriskEventType, emit_trisk_event
from src.platform_core.events.projector import list_recent_events, project_evidence_timeline
from src.platform_core.governance.audit_report import build_audit_governance_report


def _audit_tool(tool_name: str, params: dict[str, Any], *, actor: str = "mcp-client") -> None:
    if os.getenv("MCP_READ_ONLY", "1") not in ("0", "false", "False"):
        pass
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    emit_trisk_event(
        TriskEventType.MCP_TOOL_INVOKED,
        aggregate_id="mcp:session",
        aggregate_type="mcp",
        actor=actor,
        payload={"tool_name": tool_name, "params_hash": params_hash, "read_only": True},
        limitations=["MCP read-only — no remediation."],
    )
    try:
        from backend.trisk_metrics import inc

        inc("mcp_tool_invocations_total", labels={"tool": tool_name})
    except Exception:
        pass
    try:
        from backend.trisk_logging import log_trisk

        log_trisk("mcp_tool_invoked", tool=tool_name, params_hash=params_hash, read_only=True)
    except Exception:
        pass


def get_proxy_status(fixture_path: str | None = None) -> dict[str, Any]:
    params = {"fixture_path": fixture_path}
    _audit_tool("get_proxy_status", params)
    if fixture_path and Path(fixture_path).is_file():
        return json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    return {
        "wininet_proxy_enabled": False,
        "limitations": ["Demo shape — use fixture_path for real snapshot."],
    }


def get_tls_status(host: str, port: int = 443) -> dict[str, Any]:
    params = {"host": host, "port": port}
    _audit_tool("get_tls_status", params)
    try:
        from src.platform_core.tls.engine import run_tls_proof

        result = run_tls_proof(f"https://{host}:{port}/")
        return result.model_dump() if hasattr(result, "model_dump") else {"host": host, "result": str(result)}
    except Exception as exc:
        return {"host": host, "port": port, "error": str(exc), "limitations": ["TLS probe failed."]}


def get_risk_report(limit: int = 50) -> dict[str, Any]:
    params = {"limit": limit}
    _audit_tool("get_risk_report", params)
    try:
        from sqlmodel import Session, select

        from backend.db import get_engine, init_trisk_schema
        from backend.db.models import IncidentRecord

        init_trisk_schema()
        with Session(get_engine()) as session:
            rows = session.exec(select(IncidentRecord).limit(limit)).all()
            return {
                "items": [
                    {
                        "incident_id": r.incident_id,
                        "classification": r.primary_classification,
                        "confidence": r.confidence,
                    }
                    for r in rows
                ],
                "limitations": ["Ordinal scores — not probability."],
            }
    except Exception:
        return {"items": [], "limitations": ["Database unavailable in MCP context."]}


def get_evidence_timeline(aggregate_id: str) -> dict[str, Any]:
    params = {"aggregate_id": aggregate_id}
    _audit_tool("get_evidence_timeline", params)
    agg = aggregate_id if aggregate_id.startswith("evidence:") else f"evidence:{aggregate_id}"
    return {"aggregate_id": agg, "timeline": project_evidence_timeline(agg)}


def run_control_tests(incident_id: str) -> dict[str, Any]:
    params = {"incident_id": incident_id}
    _audit_tool("run_control_tests", params)
    try:
        from sqlmodel import Session, select

        from backend.db import get_engine, init_trisk_schema
        from backend.db.models import ControlTestResult

        init_trisk_schema()
        with Session(get_engine()) as session:
            rows = session.exec(
                select(ControlTestResult).where(ControlTestResult.incident_id == incident_id)
            ).all()
            return {
                "incident_id": incident_id,
                "control_tests": [r.model_dump() for r in rows],
                "read_only": True,
            }
    except Exception as exc:
        return {"incident_id": incident_id, "error": str(exc), "read_only": True}


def generate_governance_report(audit_dir: str | None = None) -> dict[str, Any]:
    params = {"audit_dir": audit_dir}
    _audit_tool("generate_governance_report", params)
    path = Path(audit_dir or os.getenv("PLATFORM_DATA_DIR", "tests/fixtures/risk_analytics/audit_sample"))
    report = build_audit_governance_report(path, format="json")
    assert isinstance(report, dict)
    report["limitations"] = list(report.get("limitations") or []) + [
        "Management information — not formal audit opinion."
    ]
    return report


def list_events_tool(limit: int = 20) -> dict[str, Any]:
    params = {"limit": limit}
    _audit_tool("list_events", params)
    events = list_recent_events(limit=limit)
    return {"items": [e.model_dump(mode="json") for e in events]}

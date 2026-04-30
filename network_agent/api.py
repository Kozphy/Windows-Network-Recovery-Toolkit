from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .cli import run_diagnosis
from .safety.repair_policy import get_preview

"""FastAPI serving layer for the hybrid diagnostic agent.

This module sits in the serving stage after decision/report generation and
exposes REST endpoints used by the web UI and external clients.

Key invariants:
- `/repair/execute` requires explicit confirmation.
- Safety policy is always enforced via `get_preview`.
- Reports are loaded from local JSON files only.
"""

app = FastAPI(title="Hybrid AI Network Diagnostic Agent API", version="0.1.0")


class DiagnoseResponse(BaseModel):
    """Response schema for the diagnosis endpoint.

    Attributes:
        report_id: Persistent report identifier.
        diagnosis: Ranked diagnosis items with evidence and confidence.
        observed_issues: Canonical issue names observed by the decision engine.
        repair_preview: Policy-gated preview object for the top action.
        report_path: Filesystem path of saved report JSON.
    """

    report_id: str
    diagnosis: list[dict[str, Any]]
    observed_issues: list[str]
    repair_preview: dict[str, Any]
    report_path: str


class RepairPreviewRequest(BaseModel):
    """Request schema for resolving a repair preview."""

    action: str = Field(min_length=1)


class RepairExecuteRequest(BaseModel):
    """Request schema for executing a repair action with confirmation."""

    action: str = Field(min_length=1)
    confirm: bool


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose() -> dict[str, Any]:
    """Run diagnosis and return a report summary for clients.

    Side effects:
        - Executes collectors and decision logic.
        - Writes a JSON report file under `reports/`.

    Idempotency:
        Not idempotent due to new report ID/timestamp per invocation.

    Args:
        None.

    Returns:
        dict[str, Any]: Report summary with top-level diagnosis fields.

    Raises:
        Exceptions propagated from diagnosis pipeline or report persistence.

    Example:
        POST /diagnose -> {"report_id": "...", "diagnosis": [...]}
    """
    report = run_diagnosis(Path("reports"))
    return {
        "report_id": report["report_id"],
        "diagnosis": report["diagnosis"],
        "observed_issues": report["observed_issues"],
        "repair_preview": report["repair_preview"],
        "report_path": report["report_path"],
    }


@app.get("/reports/{report_id}")
def get_report(report_id: str) -> dict[str, Any]:
    """Load a previously generated report by identifier.

    Data assumptions:
        - Reports are stored as UTF-8 JSON under `reports/{report_id}.json`.

    Timezone assumptions:
        - Report timestamps were generated in UTC by report writer.

    Side effects:
        Reads one local file from disk.

    Idempotency:
        Idempotent while the target report file remains unchanged.

    Args:
        report_id: UUID-like identifier of the report to retrieve.

    Returns:
        dict[str, Any]: Full serialized report payload.

    Raises:
        HTTPException: 404 if report file does not exist.
        json.JSONDecodeError: If report file is corrupted.
        OSError: If file cannot be read.

    Example:
        GET /reports/123e4567-e89b-12d3-a456-426614174000
    """
    path = Path("reports") / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")

    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/repair/preview")
def repair_preview(req: RepairPreviewRequest) -> dict[str, Any]:
    """Return a policy-validated preview for a repair action.

    Args:
        req: Request containing the action key to preview.

    Returns:
        dict[str, Any]: Preview payload including commands and safety flags.

    Raises:
        HTTPException: 400 when action is unknown or disallowed by policy.

    Example:
        POST /repair/preview {"action": "flush_dns_cache"}
    """
    preview = get_preview(req.action)
    if not preview.get("allowed", False):
        raise HTTPException(status_code=400, detail=preview)
    return preview


@app.post("/repair/execute")
def repair_execute(req: RepairExecuteRequest) -> dict[str, Any]:
    """Execute approved repair commands after explicit user confirmation.

    Decision intent:
        Enforce a hard safety gate at API boundary while supporting controlled
        remediation from approved clients.

    Input assumptions:
        - `req.action` corresponds to a known policy action.
        - Caller sets `confirm=True` only after explicit user consent.

    Output guarantees:
        - Returns per-command execution results with return code and output.
        - Never executes when policy denies action or confirmation is false.

    Side effects:
        Executes shell commands on the host machine.

    Idempotency:
        Not guaranteed. Repeated calls can apply the same repair command
        multiple times depending on command semantics.

    Known failure modes:
        - Command timeout or non-zero return code.
        - Environment-specific command availability/permissions.

    Audit Notes:
        - Detection: inspect `results[*].returncode` and `stderr`.
        - Recovery: rerun diagnosis, then fallback to manual guided scripts.

    Args:
        req: Action request with mandatory confirmation boolean.

    Returns:
        dict[str, Any]: Execution summary and per-command result details.

    Raises:
        HTTPException: 400 for missing confirmation, denied action, or empty
            command set.
        subprocess.TimeoutExpired: If command execution exceeds timeout.

    Example:
        POST /repair/execute {"action": "flush_dns_cache", "confirm": true}
    """
    if req.confirm is not True:
        raise HTTPException(status_code=400, detail="Explicit confirmation required: {\"confirm\": true}")

    preview = get_preview(req.action)
    if not preview.get("allowed", False):
        raise HTTPException(status_code=400, detail=preview)

    commands = preview.get("commands", [])
    if not isinstance(commands, list) or not commands:
        raise HTTPException(status_code=400, detail="No executable commands available for action.")

    outputs: list[dict[str, Any]] = []
    for command in commands:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            timeout=40.0,
        )
        outputs.append(
            {
                "command": command,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip(),
                "stderr": (proc.stderr or "").strip(),
            }
        )

    return {
        "action": req.action,
        "confirmed": True,
        "destructive": preview.get("destructive", False),
        "executed": True,
        "results": outputs,
    }

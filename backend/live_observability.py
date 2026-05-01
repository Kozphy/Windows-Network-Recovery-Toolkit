"""Optional FastAPI routes that delegate to ``python -m src`` subprocesses.

System position:
    Same repo checkout root as ``backend/`` siblings; relies on PYTHONPATH/importability of
    ``src`` when spawned via ``sys.executable``.

Key invariants:
    Authentication reuses ``get_current_user``; routes never bypass typed confirmation strings
    required by the CLI for destructive edits.

Audit Notes:
    ``/api/proxy/disable`` feeds the confirmation phrase through subprocess stdin; monitor
    ``logs/repair_audit.jsonl`` on the host running the FastAPI process.

Engineering Notes:
    Subprocess bridging keeps ``src/`` stdlib-only while reusing identical operator semantics
    as the terminal CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth import AuthUser, get_current_user

_ROOT = Path(__file__).resolve().parent.parent


def _invoke_src_json(argv: list[str]) -> dict[str, Any]:
    """Run ``python -m src <argv>`` and parse stdout as JSON.

    Raises:
        HTTPException: On non-zero exit codes or JSON decode failure.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "src", *argv],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={"stderr": proc.stderr, "stdout": proc.stdout},
        )
    blob = proc.stdout.strip()
    if not blob:
        return {}
    try:
        return json.loads(blob)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail={"parse_error": str(exc), "stdout": blob}) from exc


def _invoke_src_text(argv: list[str]) -> str:
    """Run CLI subcommand returning raw stdout text (non-JSON commands)."""
    proc = subprocess.run(
        [sys.executable, "-m", "src", *argv],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail={"stderr": proc.stderr, "stdout": proc.stdout})
    return proc.stdout.strip()


router = APIRouter(tags=["Toolkit observability"])


@router.get("/api/proxy/status")
def api_proxy_status(_user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Expose merged HKCU proxy + parsed mapping as JSON."""
    return _invoke_src_json(["proxy-status", "--json"])


@router.get("/api/proxy/owner")
def api_proxy_owner(
    port: int | None = None,
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Resolve listener attribution for optional explicit ``port`` query param."""
    cmd = ["proxy-owner", "--json"]
    if port is not None:
        cmd.extend(["--port", str(port)])
    return _invoke_src_json(cmd)


@router.get("/api/proxy/events")
def api_proxy_events(
    tail: int = Query(10, ge=1, le=500),
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return last ``tail`` JSONL rows from disk (best-effort parse)."""
    path = _ROOT / "logs" / "proxy_guard_events.jsonl"
    if not path.is_file():
        return {"tail": [], "path": str(path)}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-tail:]
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"unparsed": line})
    return {"path": str(path), "tail": events}


class DisablePreview(BaseModel):
    clear_server: bool = False


@router.post("/api/proxy/disable-preview")
def api_proxy_disable_preview(
    body: DisablePreview,
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """Surface plaintext preview produced by CLI ``proxy-disable --dry-run``."""
    txt = _invoke_src_text(
        ["proxy-disable", "--dry-run"]
        + (["--clear-server"] if body.clear_server else []),
    )
    return {"preview_text": txt}


class DisableConfirm(BaseModel):
    confirm: bool = Field(..., description="Must be true.")
    confirmation_text: str = Field(..., min_length=1)
    clear_server: bool = False


DISABLE_PROXY_PHRASE = "DISABLE_PROXY"


@router.post("/api/proxy/disable")
def api_proxy_disable(
    body: DisableConfirm,
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Apply HKCU proxy disable via CLI after validating JSON confirmation gate."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm must be true.")
    if body.confirmation_text != DISABLE_PROXY_PHRASE:
        raise HTTPException(
            status_code=400,
            detail=f'confirmation_text must equal "{DISABLE_PROXY_PHRASE}"',
        )
    argv = ["proxy-disable"] + (["--clear-server"] if body.clear_server else [])
    proc = subprocess.run(
        [sys.executable, "-m", "src", *argv],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        input=f"{DISABLE_PROXY_PHRASE}\n",
    )
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "logged_to": str(_ROOT / "logs" / "repair_audit.jsonl"),
    }


@router.get("/api/snapshot")
def api_snapshot(_user: AuthUser = Depends(get_current_user)) -> dict[str, str]:
    """Trigger ``snapshot`` CLI; stdout contains human ``Wrote`` path marker."""
    return {"output": _invoke_src_text(["snapshot"])}


@router.post("/api/diagnose-live")
def api_diagnose_live(_user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Return JSON-only diagnose-live payload (suppresses human banner)."""
    return _invoke_src_json(["diagnose-live", "--json"])


@router.get("/api/reports/latest")
def api_reports_latest_live(_user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Serve ``last_diagnosis_live.json`` first, falling back to v1 artefact."""
    path = _ROOT / "reports" / "last_diagnosis_live.json"
    legacy = _ROOT / "reports" / "last_diagnosis.json"
    pick = path if path.is_file() else legacy
    if not pick.is_file():
        raise HTTPException(status_code=404, detail="No latest diagnosis artifact found.")
    return json.loads(pick.read_text(encoding="utf-8"))

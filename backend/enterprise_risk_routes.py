"""Enterprise Technology Risk & Control Analytics API."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.platform_auth import get_platform_principal
from platform_core.rbac import DemoPrincipal, assert_viewer_or_above

from src.platform_core.enterprise_audit.trail import export_csv_findings, export_json
from src.platform_core.risk_platform.pipeline import (
    executive_summary_markdown,
    load_case_fixture,
    run_risk_analytics_pipeline,
)

router = APIRouter(prefix="/platform/risk-analytics", tags=["risk-analytics"])

_REPO = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = "tests/fixtures/case_studies/case_1_dead_wininet_proxy.json"


class RiskAnalyticsRequest(BaseModel):
    fixture_path: str = Field(default=DEFAULT_FIXTURE)
    dry_run: bool = True


@router.post("/assess")
def assess_risk(
    body: RiskAnalyticsRequest,
    principal: DemoPrincipal = Depends(get_platform_principal),
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    if not body.dry_run:
        raise HTTPException(status_code=403, detail="risk analytics is read-only; dry_run must be true")
    try:
        fixture = load_case_fixture(body.fixture_path)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return run_risk_analytics_pipeline(fixture)


@router.get("/governance-dashboard")
def governance_dashboard(
    principal: DemoPrincipal = Depends(get_platform_principal),
    fixture: Annotated[str, Query()] = DEFAULT_FIXTURE,
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    result = run_risk_analytics_pipeline(load_case_fixture(fixture))
    return result["governance_dashboard"]


@router.get("/executive-summary")
def executive_summary(
    principal: DemoPrincipal = Depends(get_platform_principal),
    fixture: Annotated[str, Query()] = DEFAULT_FIXTURE,
    format: Annotated[str, Query()] = "markdown",
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    result = run_risk_analytics_pipeline(load_case_fixture(fixture))
    if format == "json":
        return {"summary": result, "export": export_json(result)}
    return {"markdown": executive_summary_markdown(result)}


@router.get("/risk-register")
def risk_register(
    principal: DemoPrincipal = Depends(get_platform_principal),
    fixture: Annotated[str, Query()] = DEFAULT_FIXTURE,
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    result = run_risk_analytics_pipeline(load_case_fixture(fixture))
    return {"items": result.get("risk_register", []), "count": len(result.get("risk_register", []))}


@router.get("/export/findings.csv")
def export_findings_csv(
    principal: DemoPrincipal = Depends(get_platform_principal),
    fixture: Annotated[str, Query()] = DEFAULT_FIXTURE,
) -> dict[str, str]:
    assert_viewer_or_above(principal)
    result = run_risk_analytics_pipeline(load_case_fixture(fixture))
    return {"csv": export_csv_findings(result.get("findings") or [])}

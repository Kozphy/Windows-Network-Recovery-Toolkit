"""Demo platform routes — fleet summary, replay, case studies (fixture-first)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.platform_auth import get_platform_principal
from platform_core.rbac import DemoPrincipal, assert_viewer_or_above
from src.platform_core.fleet.simulator import (
    build_audit_chain_records,
    fleet_summary_from_fixture,
    load_fleet_fixture,
    replay_fleet_fixture,
    verify_fleet_audit_chain,
)

router = APIRouter(prefix="/platform", tags=["platform-demo"])

_REPO = Path(__file__).resolve().parent.parent
CASE_STUDIES_DIR = _REPO / "tests" / "fixtures" / "case_studies"
DEFAULT_FLEET = _REPO / "tests" / "fixtures" / "fleet" / "fleet_100_endpoints.jsonl"


class FleetReplayRequest(BaseModel):
    fixture_path: str = Field(default=str(DEFAULT_FLEET))
    dry_run: bool = True


def _resolve_fixture(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_file():
        return p
    alt = _REPO / path_str
    if alt.is_file():
        return alt
    raise HTTPException(status_code=404, detail=f"fixture not found: {path_str}")


@router.get("/fleet/summary")
def fleet_summary(
    principal: DemoPrincipal = Depends(get_platform_principal),
    fixture: Annotated[str, Query()] = str(DEFAULT_FLEET),
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    path = _resolve_fixture(fixture)
    summary = fleet_summary_from_fixture(path)
    rows = load_fleet_fixture(path)
    chain = build_audit_chain_records(rows)
    ok, msg = verify_fleet_audit_chain(chain)
    summary["audit_chain"] = {"ok": ok, "message": msg, "record_count": len(chain)}
    summary["latest_timeline"] = [
        {
            "endpoint_id": r.get("endpoint_id"),
            "classification": r.get("classification"),
            "timestamp_utc": r.get("timestamp_utc"),
            "policy_decision": r.get("policy_decision"),
        }
        for r in rows[-8:]
    ]
    summary["remediation_preview_status"] = {
        "preview_only": summary.get("remediation_preview_count", 0),
        "dry_run_default": True,
        "live_mutation_blocked": True,
    }
    return summary


@router.post("/fleet/replay")
def fleet_replay(
    body: FleetReplayRequest,
    principal: DemoPrincipal = Depends(get_platform_principal),
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    if not body.dry_run:
        raise HTTPException(status_code=403, detail="fleet replay is read-only; dry_run must be true")
    path = _resolve_fixture(body.fixture_path)
    result = replay_fleet_fixture(path)
    result["dry_run"] = True
    result["limitations"] = [
        "Replay verifies deterministic digest only — not live endpoint state.",
        "Observation is not proof.",
    ]
    return result


@router.get("/demo/case-studies")
def demo_case_studies(
    principal: DemoPrincipal = Depends(get_platform_principal),
) -> dict[str, Any]:
    assert_viewer_or_above(principal)
    items: list[dict[str, Any]] = []
    for path in sorted(CASE_STUDIES_DIR.glob("case_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items.append(
            {
                "case_id": data.get("case_id"),
                "title": data.get("title"),
                "symptom": data.get("symptom"),
                "classification": (data.get("classification") or {}).get("primary_classification"),
                "proof_level": (data.get("classification") or {}).get("proof_level"),
                "policy_decision": (data.get("policy_decision") or {}).get("outcome"),
                "fixture_path": str(path.relative_to(_REPO)).replace("\\", "/"),
                "limitations": (data.get("classification") or {}).get("limitations", []),
            }
        )
    return {
        "count": len(items),
        "items": items,
        "principles": [
            "Observation != Proof",
            "Correlation != Causation",
            "Confidence != Certainty",
            "Policy Permission != Safety Guarantee",
        ],
    }

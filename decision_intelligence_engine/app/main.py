from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .audit import HashChainAuditLog
from .engine import analyze
from .models import DecisionRequest, HumanDecision, HumanDecisionResult, Recommendation

app = FastAPI(
    title="Decision Intelligence / AI Governance Engine",
    version="0.1.0",
    description=(
        "Evidence-backed decision support with explicit uncertainty, deterministic "
        "scoring, human approval, and tamper-evident audit logging."
    ),
)

AUDIT_PATH = Path(os.getenv("DI_AUDIT_PATH", "data/audit.jsonl"))
audit = HashChainAuditLog(AUDIT_PATH)
_pending: dict[str, Recommendation] = {}
_completed: dict[str, HumanDecisionResult] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "human-in-the-loop"}


@app.post("/v1/decisions/analyze", response_model=Recommendation)
def analyze_decision(request: DecisionRequest) -> Recommendation:
    recommendation = analyze(request)
    _pending[recommendation.decision_id] = recommendation
    audit.append("recommendation_created", recommendation.model_dump(mode="json"))
    return recommendation


@app.post("/v1/decisions/{decision_id}/human-decision", response_model=HumanDecisionResult)
def human_decision(decision_id: str, decision: HumanDecision) -> HumanDecisionResult:
    if decision_id not in _pending:
        if decision_id in _completed:
            raise HTTPException(status_code=409, detail="decision already finalized")
        raise HTTPException(status_code=404, detail="decision not found")

    result = HumanDecisionResult(
        decision_id=decision_id,
        action=decision.action,
        approver=decision.approver,
        rationale=decision.rationale,
        status="approved" if decision.action == "approve" else "rejected",
    )
    audit.append("human_decision_recorded", result.model_dump(mode="json"))
    _pending.pop(decision_id)
    _completed[decision_id] = result
    return result


@app.get("/v1/audit/verify")
def verify_audit() -> dict[str, object]:
    valid, records = audit.verify()
    return {"valid": valid, "records": records}

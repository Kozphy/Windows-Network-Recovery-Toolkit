from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .audit import HashChainAuditLog
from .engine import analyze
from .metrics import DECISION_CONFIDENCE, DECISIONS_ANALYZED, HUMAN_DECISIONS, OUTCOMES_VERIFIED
from .models import (
    DecisionRequest,
    HumanDecision,
    HumanDecisionResult,
    OutcomeResult,
    OutcomeVerification,
    Recommendation,
)
from .policy import approval_allowed
from .store import DecisionStore

app = FastAPI(
    title="Decision Intelligence / AI Governance Engine",
    version="0.2.0",
    description=(
        "Evidence-backed decision support with policy-as-code, durable persistence, "
        "separation of duties, human approval, outcome verification, and tamper-evident audit logging."
    ),
)

AUDIT_PATH = Path(os.getenv("DI_AUDIT_PATH", "data/audit.jsonl"))
audit = HashChainAuditLog(AUDIT_PATH)
store = DecisionStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "human-in-the-loop", "version": "0.2.0"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/decisions/analyze", response_model=Recommendation)
def analyze_decision(request: DecisionRequest) -> Recommendation:
    recommendation = analyze(request)
    store.save_recommendation(recommendation)
    audit.append("recommendation_created", recommendation.model_dump(mode="json"))
    DECISIONS_ANALYZED.labels(domain=recommendation.domain).inc()
    DECISION_CONFIDENCE.observe(recommendation.confidence)
    return recommendation


@app.get("/v1/decisions/{decision_id}", response_model=Recommendation)
def get_decision(decision_id: str) -> Recommendation:
    recommendation = store.get_recommendation(decision_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return recommendation


@app.post("/v1/decisions/{decision_id}/human-decision", response_model=HumanDecisionResult)
def human_decision(decision_id: str, decision: HumanDecision) -> HumanDecisionResult:
    recommendation = store.get_recommendation(decision_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="decision not found")

    current_status = store.get_status(decision_id)
    if current_status != "pending_human_review":
        raise HTTPException(status_code=409, detail="decision already finalized")

    if decision.approver == recommendation.requester:
        raise HTTPException(status_code=403, detail="separation of duties: requester cannot approve own decision")

    if decision.action == "approve":
        allowed, reason = approval_allowed(recommendation)
        if not allowed:
            audit.append(
                "approval_blocked_by_policy",
                {"decision_id": decision_id, "approver": decision.approver, "reason": reason},
            )
            raise HTTPException(status_code=422, detail=reason)

    result = HumanDecisionResult(
        decision_id=decision_id,
        action=decision.action,
        approver=decision.approver,
        rationale=decision.rationale,
        status="approved" if decision.action == "approve" else "rejected",
    )
    store.save_human_decision(result)
    audit.append("human_decision_recorded", result.model_dump(mode="json"))
    HUMAN_DECISIONS.labels(action=result.action).inc()
    return result


@app.post("/v1/decisions/{decision_id}/outcome", response_model=OutcomeResult)
def verify_outcome(decision_id: str, verification: OutcomeVerification) -> OutcomeResult:
    recommendation = store.get_recommendation(decision_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="decision not found")

    human_result = store.get_human_decision(decision_id)
    if human_result is None or human_result.status != "approved":
        raise HTTPException(status_code=409, detail="only approved decisions can have verified outcomes")
    if verification.verifier in {recommendation.requester, human_result.approver}:
        raise HTTPException(status_code=403, detail="outcome verifier must be independent of requester and approver")
    if store.get_outcome(decision_id) is not None:
        raise HTTPException(status_code=409, detail="outcome already verified")

    result = OutcomeResult(decision_id=decision_id, **verification.model_dump())
    store.save_outcome(result)
    audit.append("outcome_verified", result.model_dump(mode="json"))
    OUTCOMES_VERIFIED.labels(outcome=result.outcome).inc()
    return result


@app.get("/v1/audit/verify")
def verify_audit() -> dict[str, object]:
    valid, records = audit.verify()
    return {"valid": valid, "records": records}

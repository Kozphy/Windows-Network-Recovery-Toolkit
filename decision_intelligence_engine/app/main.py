from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .audit import HashChainAuditLog
from .auth import Principal, require_role
from .engine import analyze
from .evaluation import CalibrationReport, CalibrationRequest, evaluate_calibration
from .metrics import DECISION_CONFIDENCE, DECISIONS_ANALYZED, HUMAN_DECISIONS, OUTCOMES_VERIFIED
from .models import (
    DecisionRequest,
    HumanDecision,
    HumanDecisionResult,
    OutcomeResult,
    OutcomeVerification,
    Recommendation,
)
from .policy import approval_allowed, load_policy
from .store import DecisionStore
from .telemetry import configure_telemetry

app = FastAPI(
    title="Decision Intelligence / AI Governance Engine",
    version="0.3.0",
    description=(
        "Evidence-backed decision support with signed-identity role boundaries, versioned policy-as-code, "
        "durable persistence, independent approval and verification, calibration evaluation, replayable events, "
        "Prometheus metrics, OpenTelemetry hooks, and tamper-evident audit logging."
    ),
)

AUDIT_PATH = Path(os.getenv("DI_AUDIT_PATH", "data/audit.jsonl"))
audit = HashChainAuditLog(AUDIT_PATH)
store = DecisionStore()
tracer = configure_telemetry()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "human-in-the-loop",
        "version": "0.3.0",
        "policy_version": load_policy().version,
        "auth_mode": os.getenv("DI_AUTH_MODE", "disabled"),
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/decisions/analyze", response_model=Recommendation)
def analyze_decision(
    request: DecisionRequest,
    principal: Principal = Depends(require_role("requester")),
) -> Recommendation:
    request = request.model_copy(update={"requester": principal.subject})
    with tracer.start_as_current_span("decision.analyze") as span:
        span.set_attribute("decision.domain", request.domain)
        span.set_attribute("decision.requester", principal.subject)
        recommendation = analyze(request)
        span.set_attribute("decision.id", recommendation.decision_id)
        span.set_attribute("decision.confidence", recommendation.confidence)
    store.save_recommendation(recommendation)
    audit.append("recommendation_created", recommendation.model_dump(mode="json"))
    DECISIONS_ANALYZED.labels(domain=recommendation.domain).inc()
    DECISION_CONFIDENCE.observe(recommendation.confidence)
    return recommendation


@app.get("/v1/decisions/{decision_id}", response_model=Recommendation)
def get_decision(
    decision_id: str,
    _: Principal = Depends(require_role("auditor")),
) -> Recommendation:
    recommendation = store.get_recommendation(decision_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return recommendation


@app.post("/v1/decisions/{decision_id}/human-decision", response_model=HumanDecisionResult)
def human_decision(
    decision_id: str,
    decision: HumanDecision,
    principal: Principal = Depends(require_role("approver")),
) -> HumanDecisionResult:
    recommendation = store.get_recommendation(decision_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="decision not found")
    if store.get_status(decision_id) != "pending_human_review":
        raise HTTPException(status_code=409, detail="decision already finalized")
    if principal.subject == recommendation.requester:
        raise HTTPException(status_code=403, detail="separation of duties: requester cannot approve own decision")

    if decision.action == "approve":
        allowed, reason = approval_allowed(recommendation)
        if not allowed:
            audit.append(
                "approval_blocked_by_policy",
                {"decision_id": decision_id, "approver": principal.subject, "reason": reason},
            )
            raise HTTPException(status_code=422, detail=reason)

    result = HumanDecisionResult(
        decision_id=decision_id,
        action=decision.action,
        approver=principal.subject,
        rationale=decision.rationale,
        status="approved" if decision.action == "approve" else "rejected",
    )
    store.save_human_decision(result)
    audit.append("human_decision_recorded", result.model_dump(mode="json"))
    HUMAN_DECISIONS.labels(action=result.action).inc()
    return result


@app.post("/v1/decisions/{decision_id}/outcome", response_model=OutcomeResult)
def verify_outcome(
    decision_id: str,
    verification: OutcomeVerification,
    principal: Principal = Depends(require_role("verifier")),
) -> OutcomeResult:
    recommendation = store.get_recommendation(decision_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="decision not found")
    human_result = store.get_human_decision(decision_id)
    if human_result is None or human_result.status != "approved":
        raise HTTPException(status_code=409, detail="only approved decisions can have verified outcomes")
    if principal.subject in {recommendation.requester, human_result.approver}:
        raise HTTPException(status_code=403, detail="outcome verifier must be independent of requester and approver")
    if store.get_outcome(decision_id) is not None:
        raise HTTPException(status_code=409, detail="outcome already verified")

    payload = verification.model_copy(update={"verifier": principal.subject})
    result = OutcomeResult(decision_id=decision_id, **payload.model_dump())
    store.save_outcome(result)
    audit.append("outcome_verified", result.model_dump(mode="json"))
    OUTCOMES_VERIFIED.labels(outcome=result.outcome).inc()
    return result


@app.get("/v1/decisions/{decision_id}/replay")
def replay_decision(
    decision_id: str,
    _: Principal = Depends(require_role("auditor")),
) -> dict[str, object]:
    if store.get_recommendation(decision_id) is None:
        raise HTTPException(status_code=404, detail="decision not found")
    valid, _ = audit.verify()
    if not valid:
        raise HTTPException(status_code=409, detail="audit chain verification failed")
    events = audit.replay(decision_id)
    return {"decision_id": decision_id, "events": events, "event_count": len(events)}


@app.post("/v1/evaluation/calibration", response_model=CalibrationReport)
def calibration(
    request: CalibrationRequest,
    _: Principal = Depends(require_role("auditor")),
) -> CalibrationReport:
    return evaluate_calibration(request)


@app.get("/v1/audit/verify")
def verify_audit(
    _: Principal = Depends(require_role("auditor")),
) -> dict[str, object]:
    valid, records = audit.verify()
    return {"valid": valid, "records": records}

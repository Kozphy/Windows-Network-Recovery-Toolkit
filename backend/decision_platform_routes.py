"""Enterprise Decision Intelligence Platform API.

Service-oriented routes exposing Evidence, Classification, Policy, Audit, and Reporting
services with multi-tenant RBAC and human approval workflows.

Prefix: ``/v1/enterprise``

OpenAPI tags group endpoints by service boundary for enterprise operations teams.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.auth.dependencies import get_v1_principal
from backend.auth.rbac import (
    V1Principal,
    assert_can_ingest,
    assert_can_manage_policy,
    assert_can_read_audit_reports,
    assert_can_read_incidents,
    assert_can_review,
    assert_can_run_pipeline,
)
from backend.db import get_engine, init_trisk_schema
from backend.db.models import HumanReviewItem, PlatformDecisionRecord
from backend.services.audit_service import AuditService
from backend.services.base import assert_tenant_access, principal_context
from backend.services.classification_service import ClassificationService
from backend.services.evidence_service import EvidenceService
from backend.services.pipeline import run_decision_pipeline
from backend.services.policy_service import PolicyService
from backend.services.reporting_service import ReportingService

router = APIRouter(prefix="/v1/enterprise", tags=["enterprise-decision-platform"])


def _session() -> Session:
    init_trisk_schema()
    return Session(get_engine())


class ObservationRequest(BaseModel):
    endpoint_id: str = Field(min_length=1, max_length=128)
    signal_type: str = Field(min_length=1, max_length=64)
    raw_observation: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = ""


class EvidenceIngestRequest(BaseModel):
    endpoint_id: str = Field(min_length=1, max_length=128)
    evidence_type: str = Field(min_length=1, max_length=64)
    raw_snapshot: dict[str, Any] = Field(default_factory=dict)
    source_event_id: str | None = None
    evidence_tier: str = "T1_STATE_EVIDENCE"
    observation_id: str | None = None


class PipelineRequest(BaseModel):
    endpoint_id: str = Field(min_length=1, max_length=128)
    signal_type: str = Field(default="proxy_state", max_length=64)
    raw_observation: dict[str, Any] = Field(default_factory=dict)
    evidence_type: str = Field(default="proxy_state", max_length=64)
    requested_action: str = Field(default="observe", max_length=64)


class PolicyEvaluateRequest(BaseModel):
    classification: str = Field(min_length=1, max_length=64)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_tier: str = "T1_STATE_EVIDENCE"
    requested_action: str = "observe"


class PolicyPackRequest(BaseModel):
    yaml_content: str = Field(min_length=10)
    version: str = "1.0.0"
    activate: bool = True


class HumanApprovalRequest(BaseModel):
    action: str = Field(description="accept_classification | reject_remediation | request_more_evidence")
    reason: str = Field(min_length=3)


@router.get("/health", tags=["enterprise-decision-platform"])
def enterprise_health() -> dict[str, Any]:
    """Subsystem readiness for enterprise decision platform."""
    init_trisk_schema()
    return {
        "status": "ok",
        "services": [
            "evidence",
            "classification",
            "policy",
            "audit",
            "reporting",
        ],
        "pipeline": "observation→hypothesis→evidence→confidence→decision→audit",
    }


# --- Evidence Service ---

@router.post("/observations", tags=["evidence-service"])
def create_observation(
    body: ObservationRequest,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_ingest(principal)
    with _session() as session:
        svc = EvidenceService(session, principal_context(principal))
        row = svc.record_observation(
            endpoint_id=body.endpoint_id,
            signal_type=body.signal_type,
            raw_observation=body.raw_observation,
            correlation_id=body.correlation_id,
        )
        session.commit()
        return row.model_dump(mode="json")


@router.post("/evidence", tags=["evidence-service"])
def ingest_evidence(
    body: EvidenceIngestRequest,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_ingest(principal)
    with _session() as session:
        svc = EvidenceService(session, principal_context(principal))
        row, created = svc.ingest_evidence(
            endpoint_id=body.endpoint_id,
            evidence_type=body.evidence_type,
            raw_snapshot=body.raw_snapshot,
            source_event_id=body.source_event_id,
            evidence_tier=body.evidence_tier,
            observation_id=body.observation_id,
        )
        session.commit()
        return {"evidence": row.model_dump(mode="json"), "created": created}


@router.get("/evidence/{event_id}", tags=["evidence-service"])
def get_evidence(
    event_id: str,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    with _session() as session:
        svc = EvidenceService(session, principal_context(principal))
        row = svc.get_evidence(event_id)
        if not row:
            raise HTTPException(status_code=404, detail="evidence not found")
        return row.model_dump(mode="json")


# --- Classification Service ---

@router.post("/classify", tags=["classification-service"])
def classify_fixture(
    fixture: dict[str, Any],
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    with _session() as session:
        svc = ClassificationService(session, principal_context(principal))
        return svc.classify_fixture(fixture)


# --- Policy Service ---

@router.post("/policy/evaluate", tags=["policy-service"])
def evaluate_policy(
    body: PolicyEvaluateRequest,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    with _session() as session:
        svc = PolicyService(session, principal_context(principal))
        return svc.evaluate(
            classification=body.classification,
            confidence_score=body.confidence_score,
            evidence_tier=body.evidence_tier,
            requested_action=body.requested_action,
        )


@router.post("/policy/packs", tags=["policy-service"])
def register_policy_pack(
    body: PolicyPackRequest,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_manage_policy(principal)
    with _session() as session:
        svc = PolicyService(session, principal_context(principal))
        row = svc.register_policy_pack(
            yaml_content=body.yaml_content,
            version=body.version,
            activate=body.activate,
        )
        session.commit()
        return {"pack_id": row.pack_id, "version": row.version, "active": row.active}


@router.get("/policy/packs/active", tags=["policy-service"])
def get_active_policy(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    with _session() as session:
        svc = PolicyService(session, principal_context(principal))
        return svc.get_active_policy_doc()


# --- Decision Pipeline ---

@router.post("/pipeline/run", tags=["decision-pipeline"])
def run_pipeline(
    body: PipelineRequest,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    """Execute Observation → Hypothesis → Evidence → Confidence → Decision → Audit."""
    assert_can_run_pipeline(principal)
    with _session() as session:
        result = run_decision_pipeline(
            session,
            principal,
            endpoint_id=body.endpoint_id,
            signal_type=body.signal_type,
            raw_observation=body.raw_observation,
            evidence_type=body.evidence_type,
            requested_action=body.requested_action,
        )
        session.commit()
        return {
            "correlation_id": result.correlation_id,
            "observation_id": result.observation_id,
            "evidence_event_id": result.evidence_event_id,
            "hypothesis_id": result.hypothesis_id,
            "decision_id": result.decision_id,
            "incident_id": result.incident_id,
            "classification": result.classification,
            "confidence_score": result.confidence_score,
            "policy_outcome": result.policy_outcome,
            "human_approval_required": result.human_approval_required,
            "human_review_id": result.human_review_id,
            "limitations": result.limitations,
        }


@router.get("/decisions/{decision_id}", tags=["decision-pipeline"])
def get_decision(
    decision_id: str,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    with _session() as session:
        row = session.exec(
            select(PlatformDecisionRecord).where(PlatformDecisionRecord.decision_id == decision_id)
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="decision not found")
        assert_tenant_access(principal, row.tenant_id)
        return row.model_dump(mode="json")


# --- Human Approval ---

@router.post("/reviews/{review_id}/approve", tags=["human-approval"])
def human_approval(
    review_id: str,
    body: HumanApprovalRequest,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_review(principal)
    with _session() as session:
        review = session.exec(
            select(HumanReviewItem).where(HumanReviewItem.review_id == review_id)
        ).first()
        if not review:
            raise HTTPException(status_code=404, detail="review not found")

        status_map = {
            "accept_classification": "ACCEPTED",
            "reject_remediation": "REJECTED",
            "request_more_evidence": "NEEDS_MORE_EVIDENCE",
        }
        new_status = status_map.get(body.action, "CLOSED")
        review.status = new_status
        review.actor = principal.actor_id
        review.reason = body.reason
        session.add(review)

        decision = session.exec(
            select(PlatformDecisionRecord).where(
                PlatformDecisionRecord.incident_id == review.incident_id
            )
        ).first()
        if decision:
            decision.human_approval_status = "approved" if new_status == "ACCEPTED" else new_status.lower()
            decision.actor = principal.actor_id
            session.add(decision)

        audit = AuditService(session, principal_context(principal))
        audit.append(
            event_type="HumanApprovalGranted",
            resource_type="review",
            resource_id=review_id,
            payload={"action": body.action, "reason": body.reason},
        )
        session.commit()
        return {"review_id": review_id, "status": new_status, "actor": principal.actor_id}


@router.get("/reviews/pending", tags=["human-approval"])
def list_pending_reviews(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    assert_can_review(principal)
    with _session() as session:
        rows = list(
            session.exec(
                select(HumanReviewItem)
                .where(HumanReviewItem.status == "PENDING_REVIEW")
                .limit(limit)
            ).all()
        )
        return {"items": [r.model_dump(mode="json") for r in rows], "total": len(rows)}


# --- Audit Service ---

@router.get("/audit/logs", tags=["audit-service"])
def list_audit_logs(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
    limit: int = Query(default=50, ge=1, le=500),
    correlation_id: str | None = None,
) -> dict[str, Any]:
    assert_can_read_audit_reports(principal)
    with _session() as session:
        svc = AuditService(session, principal_context(principal))
        rows = svc.list_logs(limit=limit, correlation_id=correlation_id)
        return {"items": [r.model_dump(mode="json") for r in rows], "total": len(rows)}


@router.get("/audit/verify", tags=["audit-service"])
def verify_audit_chain(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_audit_reports(principal)
    with _session() as session:
        svc = AuditService(session, principal_context(principal))
        return svc.verify_chain()


# --- Reporting Service ---

@router.get("/reports/governance", tags=["reporting-service"])
def governance_report(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_audit_reports(principal)
    with _session() as session:
        svc = ReportingService(session, principal_context(principal))
        return svc.governance_report()


@router.get("/reports/executive", tags=["reporting-service"])
def executive_report(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_audit_reports(principal)
    with _session() as session:
        svc = ReportingService(session, principal_context(principal))
        return svc.decision_dashboard()


@router.get("/reports/dashboard", tags=["reporting-service"])
def decision_dashboard(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    with _session() as session:
        svc = ReportingService(session, principal_context(principal))
        return svc.decision_dashboard()

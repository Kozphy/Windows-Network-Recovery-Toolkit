"""P0 product-control-plane routes: organization -> enrollment -> heartbeat -> fleet listing.

Security posture:
- Organization scope comes from the authenticated V1 principal, never request bodies.
- Enrollment and agent secrets are returned once and stored only as hashes.
- Enrollment tokens are tenant-scoped, expiring, revocable, and single-use by default.
- Heartbeats prove agent credential possession only; they do not imply endpoint health.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.auth.dependencies import get_v1_principal
from backend.auth.rbac import V1Principal, V1Role
from backend.db import get_engine, init_trisk_schema
from backend.db.models import Endpoint
from backend.db.repositories import append_audit_chain_row
from backend.product_v1_models import AgentCredential, AgentHeartbeat, EnrollmentToken, ProductOrganization

router = APIRouter(tags=["product-control-plane"])


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _secret_hash(secret: str) -> str:
    # A deployment-specific pepper prevents a leaked DB from being sufficient to
    # validate captured bootstrap/agent secrets offline.
    pepper = os.getenv("TRISK_AGENT_TOKEN_PEPPER") or os.getenv("TRISK_API_TOKEN")
    if not pepper:
        raise HTTPException(
            status_code=500,
            detail="TRISK_AGENT_TOKEN_PEPPER (or TRISK_API_TOKEN fallback) is not configured",
        )
    return hashlib.sha256(f"{pepper}:{secret}".encode("utf-8")).hexdigest()


def _session() -> Session:
    # product_v1_models is imported above, so its metadata is registered before
    # create_all executes. This keeps the migration additive for SQLite demos.
    init_trisk_schema()
    return Session(get_engine())


def _require_admin(principal: V1Principal) -> None:
    if principal.role != V1Role.ADMIN:
        raise HTTPException(status_code=403, detail="organization/enrollment management requires admin")


def _audit(session: Session, *, event_type: str, principal: V1Principal | None, organization_id: str,
           resource_type: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
    append_audit_chain_row(
        session,
        {
            "event_type": event_type,
            "actor": principal.actor_id if principal else "agent-bootstrap",
            "organization_id": organization_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "timestamp_utc": _utc_now().isoformat(),
        },
    )


class OrganizationCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=256)


class EnrollmentTokenCreate(BaseModel):
    ttl_minutes: int = Field(default=30, ge=1, le=1440)


class AgentEnrollRequest(BaseModel):
    enrollment_token: str = Field(min_length=20, max_length=512)
    hostname: str = Field(min_length=1, max_length=256)
    agent_version: str = Field(default="unknown", max_length=64)
    os_name: str = Field(default="Windows", max_length=128)
    os_version: str | None = Field(default=None, max_length=128)


class HeartbeatRequest(BaseModel):
    heartbeat_id: str | None = Field(default=None, max_length=64)
    agent_version: str = Field(default="unknown", max_length=64)
    os_name: str = Field(default="Windows", max_length=128)
    os_version: str | None = Field(default=None, max_length=128)
    observed_at: datetime | None = None


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(
    body: OrganizationCreate,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    """Create the organization represented by the authenticated tenant context.

    The request body cannot select an organization ID; this prevents a body-level
    tenant override. The current demo auth still treats X-Api-Tenant as principal
    context and should be replaced by identity-provider membership claims later.
    """
    _require_admin(principal)
    organization_id = principal.tenant_id
    with _session() as session:
        existing = session.exec(
            select(ProductOrganization).where(ProductOrganization.organization_id == organization_id)
        ).first()
        if existing:
            return existing.model_dump(mode="json")
        row = ProductOrganization(
            organization_id=organization_id,
            display_name=body.display_name,
            created_by_actor=principal.actor_id,
        )
        session.add(row)
        _audit(
            session,
            event_type="organization.created",
            principal=principal,
            organization_id=organization_id,
            resource_type="organization",
            resource_id=organization_id,
        )
        session.commit()
        session.refresh(row)
        return row.model_dump(mode="json")


@router.post("/enrollment-tokens", status_code=status.HTTP_201_CREATED)
def create_enrollment_token(
    body: EnrollmentTokenCreate,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    """Issue a single-use bootstrap token for the principal's organization."""
    _require_admin(principal)
    organization_id = principal.tenant_id
    plaintext = f"enr_{secrets.token_urlsafe(32)}"
    token_id = f"et_{uuid.uuid4().hex}"
    now = _utc_now()
    with _session() as session:
        organization = session.exec(
            select(ProductOrganization).where(ProductOrganization.organization_id == organization_id)
        ).first()
        if not organization:
            raise HTTPException(status_code=404, detail="organization not found for current tenant")
        row = EnrollmentToken(
            token_id=token_id,
            organization_id=organization_id,
            token_hash=_secret_hash(plaintext),
            expires_at=now + timedelta(minutes=body.ttl_minutes),
            max_uses=1,
            created_by_actor=principal.actor_id,
        )
        session.add(row)
        _audit(
            session,
            event_type="enrollment_token.created",
            principal=principal,
            organization_id=organization_id,
            resource_type="enrollment_token",
            resource_id=token_id,
            details={"expires_at": row.expires_at.isoformat(), "max_uses": 1},
        )
        session.commit()
    return {
        "token_id": token_id,
        "organization_id": organization_id,
        "enrollment_token": plaintext,
        "expires_at": row.expires_at.isoformat(),
        "single_use": True,
        "warning": "This plaintext token is returned once; store it securely.",
    }


@router.post("/enrollment-tokens/{token_id}/revoke")
def revoke_enrollment_token(
    token_id: str,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    _require_admin(principal)
    with _session() as session:
        row = session.exec(
            select(EnrollmentToken).where(
                EnrollmentToken.token_id == token_id,
                EnrollmentToken.organization_id == principal.tenant_id,
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="enrollment token not found")
        if row.revoked_at is None:
            row.revoked_at = _utc_now()
            session.add(row)
            _audit(
                session,
                event_type="enrollment_token.revoked",
                principal=principal,
                organization_id=principal.tenant_id,
                resource_type="enrollment_token",
                resource_id=token_id,
            )
            session.commit()
        return {"token_id": token_id, "revoked": True}


@router.post("/agents/enroll", status_code=status.HTTP_201_CREATED)
def enroll_agent(body: AgentEnrollRequest) -> dict[str, Any]:
    """Exchange an expiring enrollment token for durable endpoint identity + agent secret."""
    token_hash = _secret_hash(body.enrollment_token)
    now = _utc_now()
    with _session() as session:
        token = session.exec(select(EnrollmentToken).where(EnrollmentToken.token_hash == token_hash)).first()
        if not token:
            raise HTTPException(status_code=401, detail="invalid enrollment token")
        if token.revoked_at is not None:
            raise HTTPException(status_code=401, detail="enrollment token revoked")
        if _as_aware(token.expires_at) <= now:
            raise HTTPException(status_code=401, detail="enrollment token expired")
        if token.use_count >= token.max_uses or token.consumed_at is not None:
            raise HTTPException(status_code=409, detail="enrollment token already consumed")

        endpoint_id = f"ep_{uuid.uuid4().hex}"
        credential_id = f"ac_{uuid.uuid4().hex}"
        plaintext_secret = f"agt_{secrets.token_urlsafe(32)}"

        endpoint = Endpoint(
            endpoint_id=endpoint_id,
            hostname=body.hostname,
            tenant_id=token.organization_id,
            created_at=now,
            updated_at=now,
        )
        credential = AgentCredential(
            credential_id=credential_id,
            organization_id=token.organization_id,
            endpoint_id=endpoint_id,
            secret_hash=_secret_hash(plaintext_secret),
        )
        session.add(endpoint)
        session.add(credential)
        token.use_count += 1
        token.consumed_at = now
        session.add(token)
        _audit(
            session,
            event_type="agent.enrolled",
            principal=None,
            organization_id=token.organization_id,
            resource_type="endpoint",
            resource_id=endpoint_id,
            details={"credential_id": credential_id, "hostname": body.hostname},
        )
        session.commit()

    return {
        "organization_id": token.organization_id,
        "endpoint_id": endpoint_id,
        "credential_id": credential_id,
        "agent_secret": plaintext_secret,
        "warning": "This agent secret is returned once; persist it in OS-protected storage.",
    }


def _authenticate_agent(authorization: str | None) -> tuple[AgentCredential, Session]:
    if not authorization or not authorization.startswith("Agent "):
        raise HTTPException(status_code=401, detail="missing Agent credential")
    secret = authorization.split(" ", 1)[1].strip()
    session = _session()
    credential = session.exec(
        select(AgentCredential).where(AgentCredential.secret_hash == _secret_hash(secret))
    ).first()
    if not credential or credential.revoked_at is not None:
        session.close()
        raise HTTPException(status_code=401, detail="invalid or revoked Agent credential")
    return credential, session


@router.post("/agents/heartbeat")
def agent_heartbeat(
    body: HeartbeatRequest,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, Any]:
    """Persist agent liveness without claiming the endpoint is healthy."""
    credential, session = _authenticate_agent(authorization)
    try:
        heartbeat_id = body.heartbeat_id or f"hb_{uuid.uuid4().hex}"
        existing = session.exec(
            select(AgentHeartbeat).where(
                AgentHeartbeat.heartbeat_id == heartbeat_id,
                AgentHeartbeat.endpoint_id == credential.endpoint_id,
            )
        ).first()
        if existing:
            return {
                "heartbeat_id": existing.heartbeat_id,
                "endpoint_id": existing.endpoint_id,
                "status": existing.status,
                "duplicate": True,
            }

        observed = body.observed_at or _utc_now()
        row = AgentHeartbeat(
            heartbeat_id=heartbeat_id,
            organization_id=credential.organization_id,
            endpoint_id=credential.endpoint_id,
            agent_version=body.agent_version,
            os_name=body.os_name,
            os_version=body.os_version,
            status="ONLINE_UNASSESSED",
            observed_at=observed,
        )
        session.add(row)
        credential.last_used_at = _utc_now()
        session.add(credential)
        endpoint = session.exec(
            select(Endpoint).where(
                Endpoint.endpoint_id == credential.endpoint_id,
                Endpoint.tenant_id == credential.organization_id,
            )
        ).first()
        if not endpoint:
            raise HTTPException(status_code=409, detail="credential endpoint mapping is invalid")
        endpoint.updated_at = _utc_now()
        session.add(endpoint)
        session.commit()
        return {
            "heartbeat_id": heartbeat_id,
            "endpoint_id": credential.endpoint_id,
            "organization_id": credential.organization_id,
            "status": "ONLINE_UNASSESSED",
            "duplicate": False,
        }
    finally:
        session.close()


@router.get("/endpoints")
def list_product_endpoints(
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """List only endpoints owned by the authenticated tenant context."""
    with _session() as session:
        endpoints = list(
            session.exec(
                select(Endpoint)
                .where(Endpoint.tenant_id == principal.tenant_id)
                .order_by(Endpoint.created_at.desc())
                .limit(limit)
            )
        )
        items: list[dict[str, Any]] = []
        for endpoint in endpoints:
            latest = session.exec(
                select(AgentHeartbeat)
                .where(
                    AgentHeartbeat.organization_id == principal.tenant_id,
                    AgentHeartbeat.endpoint_id == endpoint.endpoint_id,
                )
                .order_by(AgentHeartbeat.received_at.desc())
            ).first()
            items.append(
                {
                    "endpoint_id": endpoint.endpoint_id,
                    "hostname": endpoint.hostname,
                    "organization_id": endpoint.tenant_id,
                    "created_at": endpoint.created_at.isoformat(),
                    "last_heartbeat_at": latest.received_at.isoformat() if latest else None,
                    "agent_version": latest.agent_version if latest else None,
                    "status": latest.status if latest else "ENROLLED_NO_HEARTBEAT",
                }
            )
        return {"organization_id": principal.tenant_id, "total": len(items), "items": items}


class AgentEvidenceRequest(BaseModel):
    """Evidence payload whose identity scope is derived from the Agent credential."""

    source_event_id: str | None = Field(default=None, max_length=128)
    evidence_type: str = Field(min_length=1, max_length=64)
    timestamp_utc: str = Field(min_length=10)
    raw_snapshot: dict[str, Any] = Field(default_factory=dict)
    normalized_fields: dict[str, Any] = Field(default_factory=dict)
    evidence_tier: str = Field(default="T1_STATE_EVIDENCE", max_length=64)
    limitations: list[str] = Field(default_factory=list)
    endpoint_id: str | None = Field(default=None, max_length=128)
    organization_id: str | None = Field(default=None, max_length=64)


@router.post("/agents/evidence", status_code=status.HTTP_202_ACCEPTED)
def agent_evidence(
    body: AgentEvidenceRequest,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, Any]:
    """Ingest evidence only for the endpoint and tenant bound to the credential."""
    from backend.db.models import EvidenceEvent, IncidentRecord
    from backend.db.repositories import content_hash
    from backend.queue import get_queue_backend
    from windows_network_toolkit.evidence_schema import STANDARD_LIMITATIONS, make_event_id

    credential, session = _authenticate_agent(authorization)
    try:
        if body.endpoint_id and body.endpoint_id != credential.endpoint_id:
            raise HTTPException(status_code=403, detail="agent cannot submit evidence for another endpoint")
        if body.organization_id and body.organization_id != credential.organization_id:
            raise HTTPException(status_code=403, detail="agent cannot override organization scope")
        if not body.raw_snapshot:
            raise HTTPException(status_code=422, detail="raw_snapshot must not be empty")

        endpoint = session.exec(
            select(Endpoint).where(
                Endpoint.endpoint_id == credential.endpoint_id,
                Endpoint.tenant_id == credential.organization_id,
            )
        ).first()
        if not endpoint:
            raise HTTPException(status_code=409, detail="credential endpoint mapping is invalid")

        c_hash = content_hash(credential.endpoint_id, body.source_event_id, body.raw_snapshot)
        existing = session.exec(
            select(EvidenceEvent).where(EvidenceEvent.content_hash == c_hash)
        ).first()
        if existing:
            if existing.endpoint_id != credential.endpoint_id or existing.tenant_id != credential.organization_id:
                raise HTTPException(status_code=409, detail="evidence hash collision across tenant boundary")
            return {
                "event_id": existing.event_id,
                "endpoint_id": existing.endpoint_id,
                "organization_id": existing.tenant_id,
                "classification_status": existing.classification_status,
                "created": False,
            }

        stable = {"endpoint_id": credential.endpoint_id, "type": body.evidence_type}
        event_id = make_event_id(body.timestamp_utc, body.evidence_type, stable)
        limitations = list(body.limitations or []) + list(STANDARD_LIMITATIONS[:2])
        row = EvidenceEvent(
            event_id=event_id,
            source_event_id=body.source_event_id,
            content_hash=c_hash,
            endpoint_id=credential.endpoint_id,
            evidence_type=body.evidence_type,
            evidence_tier=body.evidence_tier,
            raw_snapshot=body.raw_snapshot,
            normalized_fields=body.normalized_fields,
            limitations=limitations,
            tenant_id=credential.organization_id,
        )
        session.add(row)
        credential.last_used_at = _utc_now()
        session.add(credential)
        _audit(
            session,
            event_type="agent.evidence_ingested",
            principal=None,
            organization_id=credential.organization_id,
            resource_type="evidence",
            resource_id=event_id,
            details={"endpoint_id": credential.endpoint_id, "evidence_type": body.evidence_type},
        )
        session.commit()

        job = get_queue_backend().enqueue_classification_job(event_id=event_id, idempotency_key=c_hash)

        # Sync local/test classification can immediately bind the created incident.
        # Async workers also receive tenant_id from the evidence row in the worker
        # hardening added alongside this route.
        session.expire_all()
        incident = session.exec(
            select(IncidentRecord).where(IncidentRecord.evidence_event_id == event_id)
        ).first()
        if incident and not incident.tenant_id:
            incident.tenant_id = credential.organization_id
            session.add(incident)
            session.commit()

        refreshed = session.exec(select(EvidenceEvent).where(EvidenceEvent.event_id == event_id)).first()
        return {
            "event_id": event_id,
            "job_id": job.job_id,
            "endpoint_id": credential.endpoint_id,
            "organization_id": credential.organization_id,
            "classification_status": refreshed.classification_status if refreshed else "pending",
            "created": True,
        }
    finally:
        session.close()


@router.get("/endpoints/{endpoint_id}")
def get_product_endpoint(
    endpoint_id: str,
    principal: Annotated[V1Principal, Depends(get_v1_principal)],
) -> dict[str, Any]:
    """Return tenant-scoped liveness and evidence-backed state separately."""
    from backend.db.models import EvidenceEvent, IncidentRecord

    with _session() as session:
        endpoint = session.exec(
            select(Endpoint).where(
                Endpoint.endpoint_id == endpoint_id,
                Endpoint.tenant_id == principal.tenant_id,
            )
        ).first()
        if not endpoint:
            raise HTTPException(status_code=404, detail="endpoint not found")

        heartbeat = session.exec(
            select(AgentHeartbeat)
            .where(
                AgentHeartbeat.organization_id == principal.tenant_id,
                AgentHeartbeat.endpoint_id == endpoint_id,
            )
            .order_by(AgentHeartbeat.received_at.desc())
        ).first()
        evidence = session.exec(
            select(EvidenceEvent)
            .where(
                EvidenceEvent.tenant_id == principal.tenant_id,
                EvidenceEvent.endpoint_id == endpoint_id,
            )
            .order_by(EvidenceEvent.created_at.desc())
        ).first()
        incident = session.exec(
            select(IncidentRecord)
            .where(
                IncidentRecord.tenant_id == principal.tenant_id,
                IncidentRecord.endpoint_id == endpoint_id,
            )
            .order_by(IncidentRecord.created_at.desc())
        ).first()

        return {
            "endpoint_id": endpoint.endpoint_id,
            "hostname": endpoint.hostname,
            "organization_id": endpoint.tenant_id,
            "liveness": {
                "status": heartbeat.status if heartbeat else "ENROLLED_NO_HEARTBEAT",
                "last_heartbeat_at": heartbeat.received_at.isoformat() if heartbeat else None,
                "agent_version": heartbeat.agent_version if heartbeat else None,
            },
            "evidence_state": {
                "event_id": evidence.event_id if evidence else None,
                "classification_status": evidence.classification_status if evidence else "NOT_ASSESSED",
                "evidence_tier": evidence.evidence_tier if evidence else None,
            },
            "latest_incident": (
                {
                    "incident_id": incident.incident_id,
                    "classification": incident.primary_classification,
                    "proof_tier": incident.proof_tier,
                    "confidence": incident.confidence,
                    "limitations": incident.limitations,
                }
                if incident
                else None
            ),
            "limitations": [
                "Heartbeat proves authenticated liveness only; health requires evidence.",
                "Confidence is ordinal and not a calibrated probability.",
            ],
        }

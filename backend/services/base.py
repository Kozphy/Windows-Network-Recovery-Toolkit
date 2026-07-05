"""Shared tenant context and service utilities."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.auth.rbac import V1Principal, V1Role
from backend.db.models import TenantRecord


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    actor_id: str
    role: V1Role


def assert_tenant_access(principal: V1Principal, tenant_id: str) -> None:
    """Operators may only access their bound tenant unless admin."""
    if principal.role == V1Role.ADMIN:
        return
    if principal.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant access denied")


def ensure_tenant(session: Session, tenant_id: str, *, display_name: str | None = None) -> TenantRecord:
    row = session.exec(select(TenantRecord).where(TenantRecord.tenant_id == tenant_id)).first()
    if row:
        return row
    tenant = TenantRecord(
        tenant_id=tenant_id,
        display_name=display_name or tenant_id,
        status="active",
    )
    session.add(tenant)
    session.flush()
    return tenant


def principal_context(principal: V1Principal) -> TenantContext:
    return TenantContext(
        tenant_id=principal.tenant_id,
        actor_id=principal.actor_id,
        role=principal.role,
    )

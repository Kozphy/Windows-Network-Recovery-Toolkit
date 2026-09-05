"""Persistence models for the first product-control-plane vertical slice.

These tables are additive to the existing technology-risk schema. Secrets are
never stored in plaintext; only SHA-256 hashes (with a deployment pepper) are
persisted by the service layer.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProductOrganization(SQLModel, table=True):
    __tablename__ = "product_organizations"

    id: int | None = Field(default=None, primary_key=True)
    organization_id: str = Field(unique=True, index=True, max_length=64)
    display_name: str = Field(max_length=256)
    created_by_actor: str = Field(max_length=128)
    created_at: datetime = Field(default_factory=utc_now)


class EnrollmentToken(SQLModel, table=True):
    __tablename__ = "product_enrollment_tokens"

    id: int | None = Field(default=None, primary_key=True)
    token_id: str = Field(unique=True, index=True, max_length=64)
    organization_id: str = Field(index=True, max_length=64)
    token_hash: str = Field(unique=True, index=True, max_length=64)
    expires_at: datetime
    revoked_at: datetime | None = Field(default=None)
    consumed_at: datetime | None = Field(default=None)
    max_uses: int = Field(default=1, ge=1)
    use_count: int = Field(default=0, ge=0)
    created_by_actor: str = Field(max_length=128)
    created_at: datetime = Field(default_factory=utc_now)


class AgentCredential(SQLModel, table=True):
    __tablename__ = "product_agent_credentials"
    __table_args__ = (
        UniqueConstraint("organization_id", "endpoint_id", name="uq_product_agent_org_endpoint"),
    )

    id: int | None = Field(default=None, primary_key=True)
    credential_id: str = Field(unique=True, index=True, max_length=64)
    organization_id: str = Field(index=True, max_length=64)
    endpoint_id: str = Field(index=True, max_length=128)
    secret_hash: str = Field(unique=True, index=True, max_length=64)
    revoked_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class AgentHeartbeat(SQLModel, table=True):
    __tablename__ = "product_agent_heartbeats"

    id: int | None = Field(default=None, primary_key=True)
    heartbeat_id: str = Field(unique=True, index=True, max_length=64)
    organization_id: str = Field(index=True, max_length=64)
    endpoint_id: str = Field(index=True, max_length=128)
    agent_version: str = Field(default="unknown", max_length=64)
    os_name: str = Field(default="Windows", max_length=128)
    os_version: str | None = Field(default=None, max_length=128)
    status: str = Field(default="ONLINE_UNASSESSED", max_length=32)
    observed_at: datetime = Field(default_factory=utc_now, index=True)
    received_at: datetime = Field(default_factory=utc_now)

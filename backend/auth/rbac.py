"""RBAC roles for /v1 technology-risk API (demo token auth)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import HTTPException


class V1Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    RISK_REVIEWER = "risk_reviewer"
    AUDITOR_READONLY = "auditor_readonly"
    DEMO_VIEWER = "demo_viewer"


@dataclass(frozen=True)
class V1Principal:
    actor_id: str
    role: V1Role
    tenant_id: str = "default"


def assert_can_manage_policy(principal: V1Principal) -> None:
    if principal.role not in (V1Role.ADMIN,):
        raise HTTPException(status_code=403, detail="policy management requires admin")


def assert_can_run_pipeline(principal: V1Principal) -> None:
    if principal.role not in (V1Role.ADMIN, V1Role.OPERATOR, V1Role.RISK_REVIEWER):
        raise HTTPException(status_code=403, detail="pipeline requires operator, reviewer, or admin")


def parse_role(raw: str | None) -> V1Role:
    if not raw:
        return V1Role.DEMO_VIEWER
    key = raw.strip().lower()
    for role in V1Role:
        if role.value == key:
            return role
    return V1Role.DEMO_VIEWER


def assert_can_ingest(principal: V1Principal) -> None:
    if principal.role not in (V1Role.ADMIN, V1Role.OPERATOR):
        raise HTTPException(status_code=403, detail="ingest requires operator or admin")


def assert_can_review(principal: V1Principal) -> None:
    if principal.role not in (V1Role.ADMIN, V1Role.RISK_REVIEWER):
        raise HTTPException(status_code=403, detail="review requires risk_reviewer or admin")


def assert_can_read_incidents(principal: V1Principal) -> None:
    if principal.role == V1Role.DEMO_VIEWER:
        return
    if principal.role in (V1Role.ADMIN, V1Role.OPERATOR, V1Role.RISK_REVIEWER, V1Role.AUDITOR_READONLY):
        return
    raise HTTPException(status_code=403, detail="read incidents denied")


def assert_can_read_audit_reports(principal: V1Principal) -> None:
    if principal.role in (
        V1Role.ADMIN,
        V1Role.RISK_REVIEWER,
        V1Role.AUDITOR_READONLY,
        V1Role.DEMO_VIEWER,
    ):
        return
    raise HTTPException(status_code=403, detail="audit/report read denied")

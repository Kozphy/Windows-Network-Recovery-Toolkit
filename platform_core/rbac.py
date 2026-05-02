"""Demo-mode RBAC using HTTP headers (localhost portfolio only — not a substitute for IdP)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException

Role = Literal["viewer", "operator", "admin", "security_auditor"]


@dataclass(frozen=True)
class DemoPrincipal:
    """Resolved identity for ``X-Operator-*`` headers."""

    operator_id: str
    role: Role


def _normalize_role(raw: str | None) -> Role:
    r = (raw or os.getenv("PLATFORM_DEFAULT_ROLE") or "operator").strip().lower()
    if r in ("viewer", "operator", "admin", "security_auditor"):
        return r  # type: ignore[return-value]
    return "operator"


def parse_demo_principal(
    x_operator_id: str | None,
    x_operator_role: str | None,
) -> DemoPrincipal:
    """Build a principal from optional demo headers (defaults: operator / anonymous id)."""

    oid = (x_operator_id or os.getenv("PLATFORM_DEFAULT_OPERATOR_ID") or "anonymous").strip()
    role = _normalize_role(x_operator_role)
    return DemoPrincipal(operator_id=oid, role=role)


def assert_can_preview(principal: DemoPrincipal) -> None:
    if principal.role not in ("operator", "admin"):
        raise HTTPException(status_code=403, detail="remediation preview requires operator or admin")


def assert_can_execute(principal: DemoPrincipal, *, dry_run: bool) -> None:
    if principal.role not in ("operator", "admin"):
        raise HTTPException(status_code=403, detail="remediation execute requires operator or admin")
    if principal.role == "operator" and not dry_run:
        raise HTTPException(
            status_code=403,
            detail="operator role may only run dry_run executions; use admin for live allowlisted repair",
        )


def assert_can_read_audit(principal: DemoPrincipal) -> None:
    if principal.role not in ("admin", "security_auditor"):
        raise HTTPException(status_code=403, detail="audit log restricted to admin or security_auditor")


def assert_can_ingest_failure_event(principal: DemoPrincipal) -> None:
    """Agent ingestion path: operators and admins only (viewer is read-only)."""

    if principal.role not in ("operator", "admin"):
        raise HTTPException(status_code=403, detail="ingest requires operator or admin")

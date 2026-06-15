"""Remediation lifecycle management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import RemediationState


class RemediationItem(BaseModel):
    remediation_id: str
    finding_id: str
    owner: str
    due_date: str
    action_plan: str
    status: RemediationState = RemediationState.OPEN
    dry_run_required: bool = True
    limitations: list[str] = Field(default_factory=list)

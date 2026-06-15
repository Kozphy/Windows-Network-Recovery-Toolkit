"""Create remediation items from findings — preview-only posture."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.platform_core.enterprise.enums import RemediationState
from src.platform_core.findings.models import Finding
from src.platform_core.remediation_lifecycle.models import RemediationItem


def create_remediations(findings: list[Finding], fixture: dict[str, Any]) -> list[RemediationItem]:
    preview = fixture.get("remediation_preview") or {}
    blocked = preview.get("blocked_reason")
    items: list[RemediationItem] = []
    for finding in findings:
        status = RemediationState.PLANNED if not blocked else RemediationState.OPEN
        plan = finding.recommendation
        if blocked:
            plan = f"{plan} | Blocked: {blocked}"
        due = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")
        items.append(
            RemediationItem(
                remediation_id=f"REM-{uuid.uuid4().hex[:8]}",
                finding_id=finding.finding_id,
                owner="IT Operations",
                due_date=due,
                action_plan=plan,
                status=status,
                dry_run_required=True,
                limitations=[
                    "Remediation preview only — typed confirmation required for live apply.",
                    "Policy permission is not a safety guarantee.",
                ],
            )
        )
    return items

from __future__ import annotations

from dataclasses import dataclass

from .models import AIDecisionRecord, ApprovalRecord, ControlResult, RiskRating


@dataclass(frozen=True)
class GovernanceDecision:
    allowed: bool
    reasons: tuple[str, ...]


class AIGovernanceAssuranceService:
    """Policy gate for auditable AI-assisted actions.

    The service deliberately separates AI recommendation from execution. High-risk
    actions require explicit human approval and every action requires passing controls.
    """

    def evaluate(self, record: AIDecisionRecord) -> GovernanceDecision:
        reasons: list[str] = []

        if not record.controls:
            reasons.append("no control evidence attached")
        elif not record.controls_passed:
            failed = [c.control_id for c in record.controls if not c.passed]
            reasons.append(f"failed controls: {', '.join(failed)}")

        if record.requires_human_approval:
            if record.approval is None:
                reasons.append("human approval required")
            elif not record.approval.approved:
                reasons.append("human approval denied")

        if not record.lineage:
            reasons.append("data lineage missing")

        if not record.rationale_summary.strip():
            reasons.append("decision rationale missing")

        return GovernanceDecision(allowed=not reasons, reasons=tuple(reasons))

    def attach_approval(
        self,
        record: AIDecisionRecord,
        *,
        approver: str,
        role: str,
        approved: bool,
        rationale: str,
    ) -> AIDecisionRecord:
        return record.model_copy(
            update={
                "approval": ApprovalRecord(
                    approver=approver,
                    role=role,
                    approved=approved,
                    rationale=rationale,
                )
            }
        )

    def verify_action(self, record: AIDecisionRecord, *, successful: bool) -> AIDecisionRecord:
        return record.model_copy(
            update={"verification_status": "verified" if successful else "failed"}
        )

    @staticmethod
    def baseline_controls() -> list[ControlResult]:
        """Example controls mapped to common AI assurance themes."""
        return [
            ControlResult(
                control_id="AI-GOV-01",
                framework="NIST AI RMF / ISO 42001",
                objective="Model and prompt versions are uniquely identifiable.",
                passed=True,
            ),
            ControlResult(
                control_id="AI-DATA-01",
                framework="NIST AI RMF / ISO 42001",
                objective="Input data lineage is retained for replay and audit.",
                passed=True,
            ),
            ControlResult(
                control_id="AI-HITL-01",
                framework="Internal Control",
                objective="High-risk AI actions require accountable human approval.",
                passed=True,
            ),
            ControlResult(
                control_id="AI-VER-01",
                framework="Internal Control",
                objective="Executed actions are independently verified and rollback-capable.",
                passed=True,
            ),
        ]

    @staticmethod
    def risk_from_score(score: float) -> RiskRating:
        if not 0 <= score <= 1:
            raise ValueError("risk score must be between 0 and 1")
        if score >= 0.85:
            return RiskRating.CRITICAL
        if score >= 0.65:
            return RiskRating.HIGH
        if score >= 0.35:
            return RiskRating.MEDIUM
        return RiskRating.LOW

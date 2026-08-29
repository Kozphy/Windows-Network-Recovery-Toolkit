from __future__ import annotations

from datetime import datetime, timezone

from .models import AgentRequest, AgentResponse, ProposedAction, ToolCall
from .retrieval import retrieve


class AgentOrchestrator:
    """Deterministic agent baseline with retrieval, tool proposal, approval, and audit."""

    def __init__(self) -> None:
        self.actions: dict[str, ProposedAction] = {}
        self.audit_events: list[dict[str, object]] = []

    def handle(self, request: AgentRequest) -> AgentResponse:
        evidence_items = retrieve(request.message)
        evidence = [f"{item.source}: {item.text}" for item in evidence_items]

        message = request.message.lower()
        proposed_action: ProposedAction | None = None
        if "proxy" in message:
            proposed_action = ProposedAction(
                tool=ToolCall(name="inspect_proxy", arguments={"incident_id": request.incident_id or "unbound"}),
                risk="low",
                reason="Collect deterministic proxy evidence before remediation.",
                requires_approval=False,
            )
        elif any(term in message for term in ("fix", "repair", "remediate", "reset")):
            proposed_action = ProposedAction(
                tool=ToolCall(name="propose_recovery", arguments={"incident_id": request.incident_id or "unbound"}),
                risk="medium",
                reason="A state-changing recovery action requires human approval.",
                requires_approval=True,
            )

        if proposed_action:
            self.actions[proposed_action.id] = proposed_action

        answer = "I collected grounded evidence and produced a policy-gated next step."
        if not evidence:
            answer = "No grounded runbook match was found; escalate or gather more evidence before remediation."

        self._audit(
            "agent_response",
            conversation_id=request.conversation_id,
            incident_id=request.incident_id,
            proposed_action_id=proposed_action.id if proposed_action else None,
        )
        return AgentResponse(
            conversation_id=request.conversation_id,
            answer=answer,
            evidence=evidence,
            proposed_action=proposed_action,
        )

    def get_action(self, action_id: str) -> ProposedAction | None:
        return self.actions.get(action_id)

    def set_approval(self, action_id: str, approved: bool) -> None:
        action = self.actions[action_id]
        action.approved = approved
        self._audit("approval", action_id=action_id, approved=approved, risk=action.risk)

    def _audit(self, event_type: str, **fields: object) -> None:
        self.audit_events.append(
            {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **fields,
            }
        )

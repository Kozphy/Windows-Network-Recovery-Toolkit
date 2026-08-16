from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .agent import AgentOrchestrator
from .models import AgentRequest, AgentResponse, ApprovalRequest, IncidentCreate, IncidentRecord

app = FastAPI(title="AI Technology Risk & Recovery Platform", version="0.1.0")
agent = AgentOrchestrator()
incidents: dict[str, IncidentRecord] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/incidents", response_model=IncidentRecord)
def create_incident(payload: IncidentCreate) -> IncidentRecord:
    incident = IncidentRecord.from_create(payload)
    incidents[incident.id] = incident
    return incident


@app.post("/api/agent/chat", response_model=AgentResponse)
def chat(payload: AgentRequest) -> AgentResponse:
    return agent.handle(payload)


@app.post("/api/actions/{action_id}/approve")
def approve(action_id: str, payload: ApprovalRequest) -> dict[str, str | bool]:
    action = agent.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="action not found")
    agent.set_approval(action_id, payload.approved)
    return {"action_id": action_id, "approved": payload.approved, "status": "recorded"}


@app.get("/api/audit")
def audit() -> list[dict[str, object]]:
    return agent.audit_events

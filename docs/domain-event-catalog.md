# Domain Event Catalog

Canonical events for the technology-risk loop (`trisk_domain_events.jsonl` + optional Postgres).

| Event type | Emitted when | Aggregate |
|------------|--------------|-----------|
| `EvidenceCollected` | `POST /v1/evidence` succeeds | `evidence:{event_id}` |
| `IncidentDetected` | Worker creates incident | `incident:{incident_id}` |
| `RiskClassified` | Risk score attached | `incident:{incident_id}` |
| `ControlTestCompleted` | Control tests stored | `incident:{incident_id}` |
| `HumanApprovalGranted` | Review action recorded | `incident:{incident_id}` |
| `GovernanceReportGenerated` | Executive report requested | `report:executive` |
| `McpToolInvoked` | MCP tool called | `mcp:session` |

## Envelope

```json
{
  "event_id": "devt-...",
  "event_type": "EvidenceCollected",
  "aggregate_id": "evidence:abc123",
  "sequence": 1,
  "timestamp_utc": "2026-06-12T10:00:00Z",
  "actor": "operator",
  "payload": {},
  "limitations": ["Triage only — not malware verdict."]
}
```

## Relationship to audit chain

- **Domain events** — operational timeline for agents/UI/MCP
- **Audit chain** — hash-chained governance records (`chain_of_custody.py`)

Both append-only. See [ADR-011](adr/ADR-011-unified-domain-event-log.md).

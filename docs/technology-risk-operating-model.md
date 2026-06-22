# Technology Risk Operating Model

Portfolio operating model — not enterprise policy.

## Roles

| Role | Responsibilities |
|------|------------------|
| Operator | Ingest evidence, run collectors |
| Risk reviewer | Human review queue, override classification |
| Auditor (read-only) | Audit verify, executive reports, event timeline |
| Committee | Consumes governance reports — management information |

## Cadence

- **Daily:** Review human queue depth metric
- **Weekly:** Run `fleet-benchmark` or classifier-benchmark regression
- **Per incident:** Evidence → classification → controls → review if required

## Outputs

- Domain event timeline
- Hash-chained audit JSONL
- Executive governance report
- Power BI CSV export (offline)

## Extensions (future)

- Sysmon/ETW writer proof for T4 tier
- ServiceNow/Jira webhook on `PENDING_REVIEW`
- Entra ID for `/v1` auth

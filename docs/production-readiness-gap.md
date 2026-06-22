# Production readiness gap matrix

**Status:** Production-shaped portfolio prototype — honest gap table. Not production-certified.

See also: [production_readiness.md](production_readiness.md), [classifier-evaluation-report.md](classifier-evaluation-report.md), [human-review-workflow.md](human-review-workflow.md), [evidence-replay-benchmark.md](evidence-replay-benchmark.md).

| Area | Current Portfolio Prototype | Production Requirement | Gap | Recommended Next Step |
|------|----------------------------|------------------------|-----|------------------------|
| Endpoint evidence collection | WNT CLI + fixture inject | Signed agent with scheduled collection | No fleet agent | Package Windows service agent |
| Fixture replay | `replay-benchmark` + deterministic pipeline tests | Continuous replay in CI on every classifier change | Manual local runs | Gate merges on benchmark thresholds |
| Classifier evaluation | `classifier-benchmark` offline harness | Versioned golden set + drift alerts | No hosted eval service | Publish benchmark CSV in CI artifacts |
| Registry writer proof | Sysmon E13 optional; correlation capped | Mandatory writer telemetry for PROVEN tier | Writer proof optional | Enforce T4 gate in production agent |
| Audit storage | Local JSONL + hash chain tests | WORM / immutability + retention | No external anchor | Object store with lifecycle policy |
| Authentication | Demo API without auth on `/trisk/*` | OAuth2 / mTLS | Open read endpoints | Entra ID + API keys per tenant |
| RBAC | Policy registry; no role-scoped API execute | Role-based execute and export | No RBAC middleware | Map roles to preview vs execute |
| Multi-tenant data separation | Single-tenant local paths | Tenant-scoped storage and RLS | Shared demo paths | Partition `PLATFORM_DATA_DIR` by tenant |
| API rate limiting | None in demo stack | Per-tenant quotas | Unlimited reads | Add gateway rate limits |
| Observability | Prometheus/Grafana in full compose | SLO dashboards + tracing | Demo stack only | Define SLIs for ingest and audit writes |
| Alerting | Manual review of reports | PagerDuty on control FAIL spikes | No alert routing | Alert on `human_review` queue depth |
| Power BI Service deployment | Static CSV export + blueprint | Scheduled refresh + RLS in tenant | No deployed dataset | Fabric workspace + gateway |
| Incident retention policy | Documented only | Legal hold + retention schedules | Unbounded local JSONL | Retention job with legal review |
| Human review workflow | `human_review.jsonl` module | Ticketing integration (ServiceNow/Jira) | No external queue | Webhook on `PENDING_REVIEW` |
| Legal / compliance review | Non-claims in docs | Legal sign-off on export templates | Template review pending | Review governance report wording |
| Enterprise security review | Threat model + contract tests | STRIDE + pen test | No formal review | Schedule against [threat-model.md](threat-model.md) |
| Deployment packaging | Docker compose + Makefile | GitOps + signed releases | Manual deploy | Helm chart + signed images |
| Endpoint agent signing | Unsigned Python module | Authenticode MSI | Trust warnings | Sign releases; publish SBOM |
| Privacy / data minimization | Synthetic fixtures in git | Field-level redaction at ingest | PII risk in exports | Redact-before-export in agent |
| Unified domain event log | `trisk_domain_events` JSONL + Postgres | Stream processing at scale | File-based append | Kafka/EventStore when fleet scale |
| MCP read-only tools | `mcp_server/` Phase 3 | Enterprise MCP gateway | Demo stdio server | Hosted MCP with OAuth |
| Playwright browser evidence | `browser-evidence` CLI + fixtures | Headless fleet capture | Optional dep; CI uses fixtures | Scheduled browser probes |
| Agent orchestration | Contract JSON + deterministic stub | Multi-agent LLM with guardrails | No autonomous loop yet | Phase 6 deferred |

**Positioning:** Architecture and safety contracts are demonstrated — this is not a shipped enterprise product.

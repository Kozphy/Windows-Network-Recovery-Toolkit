# Production readiness gap analysis

**Status:** Portfolio / prototype — honest gap table for reviewers and hiring panels.

See also: [production_readiness.md](production_readiness.md) (checklist), [production_deployment.md](production_deployment.md) (Compose stack).

---

| Area | Current state (honest) | Production requirement | Risk if not addressed | Recommended next step |
|------|------------------------|------------------------|----------------------|------------------------|
| Endpoint collection | WNT CLI on operator laptop; fixture inject for CI | Scheduled agent on each endpoint with signed config | Stale or missing evidence; manual coverage gaps | Package Windows service agent with heartbeat + config channel |
| Windows agent packaging | Python module + optional `src` shim; no MSI | Signed MSI/MSIX with auto-update channel | Trust and deployment friction; unsigned binary warnings | Build signed installer; document elevation model |
| Code signing | Not signed in repo | Authenticode for binaries and scripts | SmartScreen / AppLocker blocks; supply-chain doubt | Sign releases in CI; publish SBOM |
| Fleet ingestion | `fleet-simulate` JSONL + manual upload | Durable queue (Event Hub / Kafka) with idempotent ingest | Lost incidents; duplicate processing | Add ingest API with dedupe keys and backpressure |
| Storage | Local `.audit/` JSONL; optional Postgres in full Compose | Encrypted object store + retention policy | Tampering; unbounded disk; compliance gaps | WORM or immutability layer; lifecycle rules |
| Auth / RBAC | API fixture mode; no auth on `/trisk/*` demo | OAuth2 / mTLS per tenant; role-scoped execute | Unauthorized remediation attempts | Integrate Entra ID; block execute without role |
| Audit immutability | Append-only writes; hash chain in tests | Cryptographic chain + external anchor | Undetected log tampering | Ship `audit-verify` as mandatory post-ingest step |
| Secrets handling | Env vars in Compose examples | Vault / Key Vault with rotation | Leaked credentials in logs | Remove secrets from compose; use secret refs |
| Observability | Prometheus/Grafana in full stack only | SLO dashboards + alert routing | Silent failures in fleet pipeline | Define SLIs for ingest lag and audit write errors |
| Deployment | `docker-compose.yml` + `docker-compose.demo.yml` | GitOps / blue-green with health gates | Bad rollouts break reviewers and pilots | Add Helm chart; smoke tests on deploy |
| Update mechanism | Manual `git pull` / image rebuild | Staged rollout with rollback | Broken agent fleet | Versioned agent channel with canary % |
| Privacy / data minimization | Redaction helpers; synthetic fixtures in git | Field-level redaction at ingest | PII in shared audit exports | Enforce redact-before-export in agent |
| Security review | Threat model docs + contract tests | Formal STRIDE review + pen test | Unknown abuse paths | Schedule review against [threat-model.md](threat-model.md) |
| Incident response workflow | CLI replay + governance report | Ticketing integration + runbook links | Slow operator response | Webhook to ServiceNow/Jira on FAIL controls |
| Power BI / reporting deployment | Static export + blueprint docs | Scheduled refresh + RLS in tenant | Stale executive view | Deploy dataset to Fabric with gateway |

---

**Positioning:** This repository demonstrates architecture and safety contracts for technology risk evidence — not a shipped enterprise product. Gaps above are intentional scope boundaries for a portfolio prototype.

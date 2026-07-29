# Continuous Monitoring (CM)

In this repository, **CM means Continuous Monitoring**: continuously collecting and evaluating operational, reliability, control, and audit signals after software is tested and deployed.

The lifecycle is:

```text
CI → CT → CD → CM
```

| Stage | Meaning in WNRT |
|---|---|
| **CI — Continuous Integration** | Merge code frequently; run lint, type checks, safety contracts, and builds. |
| **CT — Continuous Testing** | Repeatedly test classifiers, policy gates, replay determinism, API behavior, and Windows-specific paths. |
| **CD — Continuous Delivery / Deployment** | Build immutable images and deploy approved versions through the configured workflow. |
| **CM — Continuous Monitoring** | Observe runtime health, proxy drift, control failures, audit integrity, and service readiness without silently authorizing remediation. |

## Purpose

CM closes the feedback loop after deployment. It answers questions such as:

- Is the API healthy and ready?
- Are Windows endpoints developing WinINET/WinHTTP drift?
- Is a configured localhost proxy no longer listening or forwarding traffic?
- Are control-test failure rates increasing?
- Are audit events being written and remaining verifiable?
- Did a deployment introduce a reliability regression?
- Does an incident require human review or an approved maintenance window?

CM is **evidence collection and evaluation**, not autonomous repair.

## Existing monitoring surfaces

The repository already contains monitoring-oriented components that can be composed into CM:

| Surface | Evidence / command | Role |
|---|---|---|
| API health | `GET /health`, `GET /trisk/health` | Liveness and demo-mode status |
| Platform readiness | `GET /platform/ready` | Deployment readiness check |
| Metrics | Prometheus + Grafana compose services, `/metrics` where enabled | Service and platform telemetry |
| Proxy state watch | `python -m windows_network_toolkit proxy-watch` | Detect WinINET proxy transitions |
| Localhost watch | `python -m windows_network_toolkit localhost-watch` | Repeatedly check a local application path |
| Dead-proxy guardian | `python -m src proxy-guardian --once` or `--loop` | Evaluate dead/broken proxy conditions; dry-run by default |
| Startup observability | `python -m src proxy-boot-trace`, `collect-evidence-bundle`, `startup-observability-report` | Capture startup-time drift and timing evidence |
| Audit verification | `python -m windows_network_toolkit audit verify <jsonl>` | Detect audit-chain integrity failures |
| Risk KPIs | `risk-kpi-summary`, `governance-report`, Power BI export | Aggregate incidents and control outcomes |
| Scheduled security checks | `.github/workflows/security.yml` | Dependency and image scanning |

## CM signal model

Every monitor should produce structured evidence rather than an unqualified verdict.

Recommended event envelope:

```json
{
  "schema_version": "continuous_monitoring.v1",
  "timestamp": "2026-07-30T04:30:00+08:00",
  "monitor_id": "proxy-path-health",
  "target_id": "endpoint-001",
  "signal": "LOCALHOST_PROXY_UNREACHABLE",
  "status": "FAIL",
  "severity": "HIGH",
  "proof_tier": "T2",
  "evidence_refs": ["audit://proxy-health/evt-123"],
  "limitations": [
    "No registry-writer evidence is available.",
    "This signal does not prove malware, compromise, or intent."
  ],
  "recommended_action": "CREATE_REMEDIATION_PREVIEW",
  "execution_authority": "HUMAN_APPROVAL_REQUIRED"
}
```

Important separation:

```text
Signal → Classification → Control evaluation → Alert → Human review
                                              ↘ Remediation preview
```

An alert must not directly become an execution command.

## Suggested monitors

### 1. Service availability

Monitor:

- API liveness and readiness
- response latency
- HTTP error rate
- database and Redis connectivity where configured
- container restart count

Example checks:

```powershell
curl.exe -fsS http://127.0.0.1:8000/health
curl.exe -fsS http://127.0.0.1:8000/platform/ready
```

### 2. Windows proxy-path reliability

Monitor:

- WinINET `ProxyEnable` and `ProxyServer`
- WinHTTP proxy state
- localhost listener availability
- proxy forwarding result
- direct-path result
- repeated state transitions or suspected reversion

Example:

```powershell
python -m windows_network_toolkit proxy-watch --interval 5 --format human --coalesce-ms 1000
python -m windows_network_toolkit localhost-watch --url "http://localhost:61161/ChtPopupForm" --interval 5 --duration 300
```

Listener identity remains correlation only unless registry-writer evidence exists.

### 3. Control effectiveness

Track rates and trends for:

- `PASS`
- `FAIL`
- `PARTIAL`
- `NOT_TESTED`

Possible indicators:

- control failure ratio
- endpoints with repeated drift
- incidents without sufficient proof tier
- remediation previews awaiting review
- mean time to acknowledge
- mean time to recover
- recurrence after approved remediation

### 4. Audit integrity

Monitor:

- missing audit writes
- malformed JSONL rows
- hash-chain verification failures
- duplicate or out-of-order event identifiers
- missing `limitations[]`
- actions lacking an approval or confirmation reference

Example:

```powershell
python -m windows_network_toolkit audit verify tests/fixtures/analytics/audit_sample/incidents.jsonl
```

A verification failure should create a governance alert, not rewrite or delete the audit history.

### 5. Deployment regression

After deployment, compare a bounded post-deploy window against the prior baseline:

- readiness failures
- p95 latency
- error rate
- incident classification volume
- control failure rate
- Windows proxy-path failures

Rollback remains an explicit operator decision using an immutable prior image SHA.

## Alert policy

Recommended alert levels:

| Level | Meaning | Default response |
|---|---|---|
| `INFO` | Expected state or low-risk change | Record only |
| `WARNING` | Degradation or incomplete evidence | Review during normal operations |
| `HIGH` | Repeated failure or material control breach | Notify owner and create review item |
| `CRITICAL` | Service unavailable, audit integrity failure, or widespread endpoint impact | Escalate immediately; prepare rollback/remediation preview |

Alerts should include:

- what changed
- first and latest observed timestamps
- affected targets
- evidence references
- proof tier
- limitations
- relevant control IDs
- policy result
- recommended next step
- required approver

## Safety boundaries

Continuous Monitoring does **not** mean continuous autonomous remediation.

The following rules remain mandatory:

1. Observation is not proof.
2. Correlation is not causation.
3. Classification is not accusation.
4. A monitor may recommend or create a remediation preview, but it may not silently execute registry changes.
5. Process kill, firewall reset, and adapter disable remain blocked by default.
6. AI may summarize evidence or explain an alert; it may not authorize execution.
7. A green dashboard does not prove that every endpoint is safe or healthy.
8. A failed monitor does not prove malware or malicious intent.

## Portfolio and interview framing

A concise description:

> WNRT implements CI, Continuous Testing, and deployment workflows, then closes the loop with Continuous Monitoring. CM observes API readiness, Windows proxy-path drift, control-test outcomes, and audit integrity. Signals remain evidence-backed and limitation-aware; alerts can create a human-review or remediation-preview path but never bypass policy gates.

This demonstrates:

- SRE-style observability and post-deploy feedback
- Technology Risk control monitoring
- evidence lineage and auditability
- safe automation boundaries
- measurable reliability and governance outcomes

## Implementation roadmap

### Phase 1 — documentation and inventory

- Define CM terminology and safety boundaries.
- Inventory existing health, readiness, metrics, watcher, guardian, and audit-verification surfaces.
- Map each monitor to a control owner and evidence store.

### Phase 2 — normalized monitoring events

- Introduce `continuous_monitoring.v1` event schema.
- Add deterministic status and severity mapping.
- Require `limitations[]`, proof tier, and evidence references.

### Phase 3 — alert evaluation

- Add threshold and recurrence rules.
- Add deduplication and alert-state transitions.
- Keep alert generation separate from remediation authorization.

### Phase 4 — dashboards and governance reporting

- Export monitor events into the existing analytics and Power BI model.
- Add availability, recurrence, control-failure, acknowledgement, and recovery KPIs.
- Provide drill-through from KPI to incident and raw evidence.

### Phase 5 — post-deploy feedback

- Run smoke and readiness checks after deployment.
- Compare bounded post-deploy metrics against a prior baseline.
- Produce an evidence-backed rollback recommendation when thresholds are exceeded.

## Related documentation

- [CI/CD guide](ci-cd.md)
- [Observability](observability.md)
- [Startup observability](startup-observability.md)
- [Dead-proxy guardian](dead-proxy-guardian.md)
- [Test strategy](test-strategy.md)
- [Safety model](safety_model.md)
- [Control matrix](control-matrix.md)
- [Rollback strategy](rollback-strategy.md)

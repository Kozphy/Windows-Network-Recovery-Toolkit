# Interview case study (Tier-1 portfolio)

## Endpoint Reliability Platform: Safe Diagnosis, Policy-Gated Remediation, and Replayable Audit

---

## Problem

Windows endpoints often appear “online” while **browser or dev-tool traffic fails**. Operators see successful ping and DNS while Chromium, Edge, or curl-via-WinINET fails with proxy or TLS errors. Flat repair scripts change registry, firewall, or stack settings without structured evidence — increasing blast radius and making post-incident review difficult.

---

## Why ping success is not browser-path success

- **WinINET** (browser) and **WinHTTP** (many CLI tools) maintain separate proxy configuration.
- Loopback proxies (`127.0.0.1:<port>`) can be enabled while the listener process is stale or respawned by a parent shell.
- ICMP success does not validate TCP 443, TLS, or HTTP proxy CONNECT paths.

The toolkit separates **L3/L4 transport** signals from **L7 browser-path** hypotheses.

---

## Constraints

- Local-first: no default telemetry upload.
- Safety-first: no silent kill, firewall reset, adapter disable, or registry write without typed confirmation.
- Honest epistemics: listener correlation is **not** registry-writer proof.
- Portfolio scope: prototype with deterministic fixtures — not claimed production EDR/antivirus.

---

## Architecture

```text
Observation → Event → State transition → Hypothesis
  → Evidence tree → Optional proof → Impact → Policy
  → Preview → Append-only audit → Replay → Dashboard/API
```

| Layer | Modules |
|-------|---------|
| CLI | `python -m src`, `scripts/*.bat` |
| Reasoning | `platform_core/reasoning_*` |
| Policy | `platform_core/policy`, `platform_core/remediation_registry.py` |
| Proof | `evidence/registry_writer_proof.py` |
| API | `backend/platform_routes.py` |
| Storage | JSONL under `logs/`, `platform_data/` |

---

## Safety model

Dual gates:

1. **Hypothesis policy** — ALLOW only when proof is CONFIRMED for scoped checks; high confidence without proof stays PREVIEW.
2. **Remediation registry** — forbidden/high/manual tiers block API execute even for admin role.

Regression tests: `tests/test_policy_safety_contract.py`, `tests/test_api_dry_run_default.py`.

---

## Policy engine

- **ALLOW** — Safe-tier path after CONFIRMED proof (execute still requires confirmation phrase at boundary).
- **PREVIEW** — Diagnose and preview only; typed confirmation before mutation.
- **BLOCK** — Low confidence, rejected proof, or forbidden action keys.

See [ADR-002](adr/ADR-002-policy-gated-remediation.md).

---

## Replay design

Stored observations + embedded policy snapshots are re-evaluated without subprocess repair or live probes. Drift detection counts when current registry rules would block previously allowed execute flags. See [ADR-003](adr/ADR-003-append-only-audit-and-replay.md).

---

## Testing strategy

- **550+ pytest cases** — offline fixtures, no Windows admin in CI.
- Safety contract suite at repo root for recruiter-visible discovery.
- API TestClient with patched `platform_data_dir` — no real subprocess on default dry-run.
- Proof tests use mocked Sysmon collectors — no telemetry install required.

---

## Trade-offs

| Choice | Benefit | Cost |
|--------|---------|------|
| JSONL vs database | Simple audit trail, easy replay | No query engine |
| Code registry vs YAML | Reviewable in PRs, typed tests | Requires deploy to change actions |
| Mock RBAC headers | Fast portfolio demo | Not production auth |
| Multiple JSONL files | Incremental feature growth | Operator must know which tail to read |

---

## What I would improve in production

- Unified audit schema v2 with single tail per environment.
- Request-id + idempotency middleware on remediation routes.
- Consolidate duplicate `proxy_guard` trees.
- mTLS or OIDC instead of header RBAC.
- Golden replay corpus in CI with enforced 100% determinism rate.

---

## 60-second interview pitch

> “I built a local-first Windows endpoint reliability prototype. It turns proxy and browser-path failures into an explicit chain: observations, events, hypotheses, optional proof, and ALLOW/PREVIEW/BLOCK policy — before any repair. Remediation defaults to dry-run, destructive actions are registry-blocked, and every preview or execute attempt appends to JSONL for deterministic replay. It’s not antivirus or EDR; it’s production-inspired diagnostics with honest limits on what correlation can prove.”

---

## Deep technical talking points

1. **Why two proxy stacks matter** — WinINET vs WinHTTP mismatch as L7 failure class.
2. **Proof vs inference** — Sysmon registry write vs port listener correlation.
3. **Policy drift replay** — Recompute gates from stored events when registry changes.
4. **Soak validation** — Proxy disable sticky checks vs respawning reverter parent.
5. **API dry-run default** — Pydantic `ExecuteIn.dry_run=True` + operator RBAC split.
6. **CI without Windows** — Fixture-driven safety regressions on Ubuntu.

---

## Demo

[docs/demo_3_minute.md](demo_3_minute.md)

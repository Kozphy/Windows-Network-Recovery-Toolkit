# Endpoint Reliability Platform

**One-liner:** A local-first platform that turns Windows proxy/browser-path failures into evidence-ranked, policy-gated, replayable incidents with safe remediation previews and auditability.

Python 3.11+ · Policy-gated · Local-first · 900+ pytest (CI)

---

## 60-second explanation

Windows can look **online** while browsers and dev tools fail: WinINET/WinHTTP proxy drift, stale localhost listeners, and DNS/HTTPS path differences are common causes. This is **not** a repair script, antivirus, or autonomous containment tool. It is **security observability** and **endpoint reliability** infrastructure: probes → evidence → policy → preview → audit → replay → API/dashboard.

**Epistemic rules:** observation ≠ proof · correlation ≠ causation · confidence is ordinal, not probability · listener match is not registry-writer proof.

---

## Why this is not just a script

| Script mindset | Platform mindset |
|----------------|------------------|
| One-off registry reset | Append-only audit + replay |
| Heuristic = guilt | Evidence levels with upgrade guards |
| Fix immediately | Policy-gated **preview** first |
| Laptop-only | Synthetic fleet (100 endpoints, 20 incidents) |

---

## Architecture

```text
probes → normalization → evidence fusion → reasoning → policy
  → remediation preview → audit → replay → API / dashboard / metrics
```

```text
┌─────────┐   ┌──────────┐   ┌─────────────┐   ┌────────┐   ┌─────────┐
│ Probes  │ → │ Events   │ → │ Evidence    │ → │ Policy │ → │ Preview │
│ WinINET │   │ JSONL    │   │ OBSERVED…   │   │ gates  │   │ dry-run │
└─────────┘   └──────────┘   │ FINAL_CAUS  │   └────────┘   └─────────┘
                             └─────────────┘        │              │
                                                    v              v
                                              ┌─────────────────────────┐
                                              │ Audit → Replay → API/UI │
                                              └─────────────────────────┘
```

Docs: [architecture.md](docs/architecture.md) · [evidence_model.md](docs/evidence_model.md) · [policy_model.md](docs/policy_model.md)

---

## Evidence model

| Level | Claim strength |
|-------|----------------|
| `OBSERVED_ONLY` | Proxy/registry state changed |
| `CORRELATED` | Listener/process match only |
| `PROVEN_REGISTRY_WRITER` | Sysmon E13 / Procmon / ETW |
| `PROVEN_NETWORK_IMPACT` | Browser path impact + writer proof |
| `FINAL_CAUSATION` | Writer + port owner or network impact |

Registry-writer proof when telemetry is available. See [docs/evidence_model.md](docs/evidence_model.md).

---

## Policy model

`ALLOW_OBSERVE` · `PREVIEW_ONLY` · `REQUIRE_TYPED_CONFIRMATION` · `BLOCK_DESTRUCTIVE` · `BLOCK_LOW_CONFIDENCE` · `CORRELATION_ONLY_ALERT`

No silent process kill · no firewall reset · no adapter disable · no registry mutation without typed confirmation · API execute `dry_run=true` by default.

See [docs/policy_model.md](docs/policy_model.md) · [docs/safety_model.md](docs/safety_model.md).

---

## 5-minute demo (no admin, no host mutation)

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
make demo-healthy
make demo-proxy-drift
make demo-final-causation
make demo-fleet-enterprise
make demo-production
```

Guide: [docs/demo_5_min.md](docs/demo_5_min.md)

---

## Safety guarantees

- Preview-only remediation by default; destructive verbs registry-blocked
- Typed confirmation for registry mutations
- Synthetic fixtures in git; real `logs/` and `platform_data/` gitignored
- Local-first — no default cloud upload

## What is not guaranteed

- Malware identification or removal
- Autonomous containment
- Writer attribution without Sysmon/Procmon-class telemetry
- Production authentication (demo RBAC headers only)

---

## API surface

| Endpoint | Purpose |
|----------|---------|
| `GET /platform/health` | Liveness |
| `GET /platform/ready` | Readiness |
| `GET /platform/metrics` | JSON KPIs |
| `GET /platform/slo` | SLO snapshot |
| `GET /platform/incidents` | Incident list |
| `GET /metrics` | Prometheus |
| `POST /platform/remediation/preview` | Policy-gated preview |
| `POST /platform/remediation/execute` | Dry-run default |

OpenAPI: `http://localhost:8000/docs` after `docker compose up`.

---

## Observability

Prometheus gauges: `proxy_drift_incidents_total`, `evidence_level_total_*`, `policy_decisions_total_*`, `remediation_preview_total`, `fleet_endpoints_total`.

Dashboard: `frontend/app/platform/` — incidents, evidence, policy, replay, SLO.

[docs/observability.md](docs/observability.md)

---

## Tests and CI

```powershell
pytest -q tests/test_policy_safety_contract.py tests/test_api_dry_run_default.py
pytest -q tests/test_evidence_level_contract.py tests/test_fixture_regression_demo.py
pytest -q
```

CI: `.github/workflows/ci.yml` — ruff, pytest, safety contracts, fixture smoke.

---

## Production readiness

Checklist: [docs/production_readiness.md](docs/production_readiness.md) · Deployment: [docs/production_deployment.md](docs/production_deployment.md)

Public release: [PUBLIC_RELEASE_CHECKLIST.md](PUBLIC_RELEASE_CHECKLIST.md)

---

## Interview case study

STAR write-up: [docs/interview_case_study_tier1.md](docs/interview_case_study_tier1.md)

**Pitch:** *Local-first Windows endpoint reliability prototype with evidence levels, policy-gated previews, append-only audit, deterministic replay, and fleet-scale demo — nothing repairs itself by default.*

---

## Known limitations

- Windows-first live probes; Linux CI uses fixtures
- Multiple legacy evidence vocabularies being unified via `platform_core/evidence_model.py`
- Black formatting debt in some modules (CI continue-on-error)

---

## Labs (experimental — not mainline)

Market events, multi-domain decision platform, edge simulation: [labs/README.md](labs/README.md)

---

## Quick links

| Topic | Doc |
|-------|-----|
| Full CLI reference | [docs/cli_reference.md](docs/cli_reference.md) |
| Threat model | [docs/threat_model.md](docs/threat_model.md) |
| Documentation index | [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md) |
| Tier-1 walkthrough | [docs/tier1_demo_walkthrough.md](docs/tier1_demo_walkthrough.md) |

---

## License

MIT — see [LICENSE](LICENSE).

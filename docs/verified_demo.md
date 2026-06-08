# Verified demo path

Runnable, test-backed commands for the Endpoint Reliability Platform portfolio demo. All steps below are **fixture-based or read-only** unless explicitly marked as Docker (local container only).

## Prerequisites

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

## One command (Windows)

```powershell
.\scripts\demo_tier1.ps1
```

Linux/macOS:

```bash
make demo-tier1
```

## Step-by-step commands

| Step | Command | Expected signal |
|------|---------|-----------------|
| 1. Diagnosis | `python -m src diagnose --fixture tests/fixtures/features_healthy_signals.json` | Primary hypothesis + confidence; writes `reports/last_diagnosis.json` |
| 2. Timeline replay | `python -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown` | Markdown sections: `PROCESS_CREATED`, `REGISTRY_VALUE_SET`, `LOCALHOST_LISTENER_OBSERVED`, `PROXY_STATE_CHANGED` |
| 3. Policy | `python -m src proxy-policy --fixture tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json --format json` | JSON `policy.decision` / `policy.severity` |
| 4. Evidence tree | `python -m src proxy-report --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown` | `# Proxy incident report` + `## Evidence tree` |
| 5. Release audit | `python tools/public_release_audit.py --tracked-only` | Exit 0; no tracked secrets/PII paths |
| 6. Safety tests | `pytest -q tests/test_policy_safety_contract.py tests/test_api_dry_run_default.py tests/test_replay_determinism.py tests/test_audit_contract.py` | 20 passed (approx.) |

## Docker local stack (optional)

```bash
cp .env.example .env
docker compose up --build
```

| Endpoint | URL | Expected |
|----------|-----|----------|
| Liveness | http://localhost:8000/platform/health | HTTP 200, JSON status |
| Readiness | http://localhost:8000/platform/ready | HTTP 200 when startup checks pass |
| Metrics | http://localhost:8000/metrics | Prometheus text exposition |
| Prometheus UI | http://localhost:9090 | Targets scrape `api:8000` |
| Grafana | http://localhost:3001 | Prometheus datasource provisioned |

In-process contract tests (no Docker daemon): `pytest -q tests/test_platform_health_routes.py tests/test_compose_platform_contract.py`

## CI evidence

- `.github/workflows/ci.yml` — jobs: `lint`, `test`, `build-smoke`, `frontend-build`
- `.github/workflows/security.yml` — Trivy filesystem + image scan (HIGH/CRITICAL; `exit-code: 0` during bootstrap)
- `docs/platform_engineering_gap_report.md` — README promise vs reality audit

## Safety boundaries (demo)

| Action | Demo behavior |
|--------|----------------|
| Registry mutation | **Not run** in tier-1 demo (fixtures only) |
| Process kill | **Blocked** by policy catalog |
| Firewall reset | **Blocked** by policy catalog |
| Adapter disable | **Blocked** by policy catalog |
| Live proxy-watch | Optional on Windows; not part of tier-1 script |

## Proof vs correlation (interview language)

| Signal | Label | Meaning |
|--------|-------|---------|
| Sysmon Event ID 13 | Optional telemetry | Can support `FINAL_CAUSATION` when present — not guaranteed on every host |
| Listener on localhost port | `LOCALHOST_LISTENER_OBSERVED` / `LISTENER_OBSERVED` | **Correlation** — process owns port; does not prove registry write |
| Registry polling diff | `CORRELATION_ONLY` | Observed state change between polls; writer unknown |
| Policy `BLOCK` | Policy outcome | Not malware confirmation |
| Fixture replay | Deterministic | Same fixture → same timeline/policy in CI |

## Platform Engineer / SRE interview framing

1. **Problem:** proxy drift breaks browsers while ICMP may still pass.
2. **Observation layer:** JSONL audit + fixtures for CI without Windows admin.
3. **Reasoning layer:** classification + policy engine with explicit decisions.
4. **Evidence layer:** timeline + evidence tree for post-incident review.
5. **Operations layer:** `/platform/health`, `/platform/ready`, `/metrics`, Prometheus/Grafana compose stack.
6. **Safety:** dry-run default, typed confirmation for mutations, no silent kill/firewall reset.

## Related docs

- [feature_inventory.md](feature_inventory.md) — capability map
- [demo_3_minute.md](demo_3_minute.md) — narrative walkthrough
- [production_deployment.md](production_deployment.md) — Docker details

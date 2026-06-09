# Endpoint Reliability Decision Platform

Portfolio-facing package: `windows_network_toolkit/`

## Philosophy

- Observation is not proof.
- Correlation is not causation.
- Confidence is not certainty.
- Policy permission is not a safety guarantee.

## Workflow

```text
Evidence → Hypothesis → Proof → Policy → Remediation → Audit
```

## CLI

```powershell
python -m toolkit replay windows_network_toolkit/examples/proxy_drift_incident.jsonl
python -m toolkit report windows_network_toolkit/examples/proxy_drift_incident.jsonl --format markdown
```

## API routes

| Route | Purpose |
|-------|---------|
| `GET /health` | Service liveness |
| `GET /platform/status` | Platform status |
| `POST /platform/diagnose` | Run pipeline on signals or fixture |
| `GET /platform/evidence/timeline` | Latest timeline |
| `GET /platform/decision/latest` | Latest decision |
| `GET /platform/audit/logs` | ERP audit JSONL tail |
| `POST /platform/replay` | Replay fixture |
| `POST /platform/remediation/preview` | Preview (platform_core) |
| `POST /platform/remediation/confirm` | Confirm alias (dry-run safe) |

## Dashboard

- Static demo: `GET /dashboard/` (FastAPI StaticFiles)
- Production UI: `frontend/app/platform/*` (Next.js)

## Examples

- `windows_network_toolkit/examples/proxy_drift_incident.jsonl`
- `windows_network_toolkit/examples/local_proxy_listener.jsonl`
- `windows_network_toolkit/examples/dns_ok_browser_fail.jsonl`
- `windows_network_toolkit/examples/registry_rewriter_observed.jsonl`

# Observability (Phase 3 — local / optional)

**Status:** In-memory metrics + structured JSON logs. No required external services (OTel, Datadog, etc.).

**Related:** [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) · [observability_architecture.md](observability_architecture.md) · [agent-deployment.md](agent-deployment.md)

---

## Design principles

| Principle | Implementation |
|-----------|----------------|
| Local-first | In-process counters/gauges; logs to stderr |
| Optional | Disable structured logs with `WNRT_STRUCTURED_LOG=0` |
| No safety weakening | Metrics describe platform behavior — not malware verdicts |
| Correlation | `trace_id` + `audit_id` on logs and spool/audit rows |

OpenTelemetry in `backend/tracing.py` remains **optional** and is not required for this layer.

---

## Structured JSON logging

Module: `src/platform_core/operability/structured_logging.py`

```python
from src.platform_core.operability import log_json, observability_scope

with observability_scope(trace_id="demo-trace", audit_id="demo-audit"):
    log_json("info", "policy_decision", decision="PREVIEW", dry_run=True)
```

Each line written to **stderr** (when enabled):

```json
{
  "timestamp": "2026-06-12T12:00:00+00:00",
  "level": "INFO",
  "message": "policy_decision",
  "trace_id": "demo-trace",
  "audit_id": "demo-audit",
  "decision": "PREVIEW",
  "dry_run": true
}
```

Disable: `WNRT_STRUCTURED_LOG=0`

---

## trace_id and audit_id propagation

Module: `src/platform_core/operability/context.py`

- `observability_scope()` binds `trace_id` (auto-generated if omitted)
- `new_audit_id()` / `set_audit_id()` for per-audit-row identifiers
- `correlation_fields()` merges ids into spool and audit payloads

Wired into:

- `windows_network_toolkit/agent/read_only.py` — agent collection cycles
- `src/logging/audit.py` — `append_jsonl()` injects ids + records metrics

---

## Metrics registry

Module: `src/platform_core/operability/metrics_registry.py`

| Metric | Type | Labels |
|--------|------|--------|
| `evidence_events_collected_total` | counter | `source` |
| `incidents_classified_total` | counter | `classification` |
| `control_tests_executed_total` | counter | `control_id`, `result` |
| `policy_decisions_total` | counter | `decision` |
| `blocked_actions_total` | counter | `action_id` |
| `remediation_previews_total` | counter | `action_id` |
| `audit_records_appended_total` | counter | — |
| `spool_queue_depth` | gauge | — |
| `agent_heartbeat_total` | counter | — |

Record events via `src/platform_core/operability/events.py`:

```python
from src.platform_core.operability.events import (
    record_incident_classified,
    record_policy_decision,
    record_blocked_action,
)
```

---

## Prometheus `/metrics` (FastAPI)

`GET /metrics` on `backend.main:app` merges:

1. Legacy `backend/prometheus_exporter.py` counters
2. JSONL-derived gauges (`platform_core.metrics`)
3. `backend/trisk_metrics.py` (Postgres/worker path when used)
4. **`src/platform_core/operability/metrics_registry.py`** (Phase 3 local counters/gauges)

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000
curl -s http://127.0.0.1:8000/metrics | findstr evidence_events_collected
```

No separate metrics port required.

---

## Agent integration

Each `agent once` cycle:

1. Opens `observability_scope()` (new `trace_id`)
2. Assigns `audit_id` on spool row
3. Increments `evidence_events_collected_total`, `agent_heartbeat_total`, `audit_records_appended_total`
4. Sets `spool_queue_depth` gauge from spool line count
5. Emits structured JSON log lines

---

## Endpoints summary

| URL | Purpose |
|-----|---------|
| `GET /health` | API liveness |
| `GET /metrics` | Prometheus text (includes operability counters) |
| `GET /platform/health` | Platform liveness |
| `GET /platform/metrics` | JSON aggregates (legacy) |

See also [observability_architecture.md](observability_architecture.md) for compose/Grafana assets.

---

## Verification

```powershell
pytest -q tests/platform_core/operability/test_observability.py
python -m windows_network_toolkit agent once --fixture tests/fixtures/agent/sample_evidence_bundle.json
```

---

## Explicit non-claims

- Not a hosted observability SaaS or SIEM replacement
- Metrics do not prove compromise or malware detection
- High-cardinality labels are avoided in the default registry
- Production log retention and alerting are operator responsibilities

# Metrics (`platform_core.metrics`)

**`GET /platform/metrics`** returns a merged dictionary:

1. **Legacy aggregates** rebuilt from **`platform_core.storage.list_metrics`** semantics (clusters, executions, previews, audit-derived blocks).
2. **Extended KPI counters** synthesized from **`platform_data/platform_signals.jsonl`** (+ optional attribution history).

## Extended counters (portfolio vocabulary)

Append rows with tolerant **`kind`** / **`signal`** fields:

| Field | Typical `kind` values | Interpretation |
| --- | --- | --- |
| **`proxy_changes_total`** | `proxy_registry_change`, `proxy_change` | Observability events for HKCU/system proxy deltas (agent-collector emitted). |
| **`proxy_enable_transitions_total`** | `proxy_enable_transition` | Discrete `ProxyEnable` flips inferred offline. |
| **`unknown_actor_events_total`** | `unknown_actor_marker` **or** `unknown_actor:true` payload | Signals where attribution lacked structured writer telemetry. |
| **`attribution_confidence_avg`** | `confidence` floats on **`attribution_sample`** rows OR rows in **`attribution_records.jsonl`** | Arithmetic mean capped to demo scale. |
| **`rollback_preview_total`** | `rollback_preview` | Rollback plans issued (manual or tooling). |
| **`rollback_execute_total`** | `rollback_execute` | Applied rollbacks (**tests only** simulate). |
| **`rollback_blocked_total`** | `rollback_blocked` | Explicit policy denials surfaced as signals. |
| **`endpoint_heartbeat_total`** | `heartbeat` inside signals file (**plus agent writes**) | Mirrors agent liveness KPIs independently of **`endpoints.jsonl`**. |
| **`incident_cluster_count`** | deterministic clustering | Mirrors **`cluster_failure_events`**. |
| **`affected_endpoint_count`** | unique endpoints across clusters | Distinct hashed endpoint identifiers. |

Signals are intentionally **additive** — missing files yield deterministic zeros suitable for Grafana/Prometheus scraping via a shim adapter later.

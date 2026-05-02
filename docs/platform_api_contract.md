# Platform API contract (`/platform/*`)

**Scope:** Local-first FastAPI routes under `backend/platform_routes.py` (also mounted on **`backend.main:app`**). **No external upload** in default code paths. **Bind `127.0.0.1`** in shared environments.

**Safety invariants**

- **Preview before execute** (`POST /platform/remediation/preview` before `.../execute`).
- **High / forbidden** tiers **never** succeed through non–dry-run executor from API.
- **Allowlisted** `scripts/*.bat` only (see `platform_core.remediation` + `platform_core.remediation_registry`).
- **Operators** may only run **`dry_run` executes**; **`admin`** required for live repair via API.
- **Arbitrary shell / adapter disable** blocked by registry + policy.

---

## Demo RBAC headers (portfolio)

| Header | Example | Notes |
|--------|---------|-------|
| `X-Operator-Id` | `local-dev-1` | Logged to audit rows as `actor`. |
| `X-Operator-Role` | `viewer` / `operator` / `admin` / `security` / `security_auditor` | **`security` aliases** **`security_auditor`**. Default when omitted: **`operator`**. |

| Role | Permissions |
|------|-------------|
| `viewer` | `GET` **health, endpoints, failure-events, incidents, normalized events, metrics** |
| `operator` | Viewer + agent **ingestion** (`heartbeat`, snapshots, failure-events) + **`POST remediation/preview`** + **`POST remediation/execute` with `dry_run:true`** + **`GET /platform/attribution/*`** |
| `admin` | Operator + **`GET` audit** + live **`dry_run:false` execute** (policy + registry gated) |
| `security_auditor` | Viewer metrics/incidents/events + **`GET` audit** + **`GET` attribution detail — no ingestion/preview** |

---

## GET `/platform/health`

**Purpose:** Liveness / build identity / safe-mode flag.

**RBAC:** open (no sensitive data).

**Response (JSON)**

```json
{
  "status": "ok",
  "backend_version": "0.4.0-platform-reliability-prototype",
  "platform_mode": "local_jsonl",
  "safe_mode": true,
  "data_dir": "C:\\...\\platform_data"
}
```

**Failure modes:** `500` rare (imports / misconfiguration).

---

## POST `/platform/agent/heartbeat`

**Purpose:** Register / refresh endpoint identity (**hashed IDs only**).

**RBAC:** **`operator`** or **`admin`** (viewer/security blocked).

**Request**

```json
{
  "endpoint_id": "deadbeef_stable_hash_fragment",
  "os_family": "Windows",
  "os_version": "10.0.26200",
  "agent_version": "0.1"
}
```

**Response**

```json
{ "stored": true, "endpoint_id": "..." }
```

**Audit:** heartbeat row appended.

---

## POST `/platform/snapshots`

**Purpose:** Persist sanitized **`EndpointSnapshot`**.

**RBAC:** **`operator`** or **`admin`**.

**Schema:** Matches `platform_core.models.EndpointSnapshot` (**redacted payloads expected**).

**Failure modes:** `422` pydantic validation.

---

## GET `/platform/endpoints`

**Purpose:** List latest-known endpoint rows (**JSONL compaction = last row wins per id client-side).

**RBAC:** open.

**Response:** `{ "endpoints": [ EndpointIdentity-ish dicts … ] }`

---

## GET `/platform/endpoints/{endpoint_id}`

**Purpose:** Lookup one endpoint heartbeat row.

**Response:** Endpoint dict.

**Failures:** `404` not found.

---

## GET `/platform/failure-events?limit=N`

**Purpose:** Paginated-ish tail read (`limit` clamped).

**RBAC:** open.

**Response:** `{ "items": [ FailureEvent dicts ] }`

---

## GET `/platform/failure-events/{event_id}`

**Purpose:** Single event + **Failure Knowledge linkage attempt**.

**Response**

```json
{
  "failure_event": { "...": "..." },
  "failure_block_linked": {
    "found": false,
    "failure_block_id": "uuid-or-empty",
    "detail": "not_in_local_failure_kb"
  }
}
```

When KB shards exist and UUID matches, `found:true` + `failure_block_summary`.

**Failures:** `404` event missing.

---

## POST `/platform/failure-events/ingest`

**Purpose:** Append FailureEvent from trusted local agent.

**RBAC:** **`operator`** or **`admin`** (bind localhost in production).

**Schema:** `platform_core.models.FailureEvent`

**Response:** `{ "stored": true, "event_id": "..." }`

---

## POST `/platform/remediation/preview`

**Purpose:** Build **`RemediationPreview`** + append JSONL + audit.

**RBAC:** **`operator` or `admin`**

**Request**

```json
{
  "endpoint_id": "hash",
  "failure_event_id": "uuid",
  "requested_action": "reset_proxy",
  "surface": "api"
}
```

**Response:** `RemediationPreview` dump (`preview_id`, `risk_level`, `confirmation_phrase`, `allowed_by_policy`, …).

**Safety rules**

- Rejects shell-injection patterns in `requested_action` (`400`).
- Unknown actions → preview with **`allowed_by_policy:false`**.

**Failures:** `403` viewer, `404` missing event, `400` invalid action.

---

## POST `/platform/remediation/execute`

**Purpose:** Execute **dry-run** or **allowlisted** Windows repair.

**RBAC:** **`operator` (dry_run only)** or **`admin`**

**Request**

```json
{
  "preview_id": "uuid",
  "confirmation_phrase": "RUN_PROXY_RESET",
  "dry_run": true,
  "actor": "legacy-field-ignored"
}
```

**Actor identity:** `X-Operator-Id` preferred (recorded as `confirmed_by`).

**Behavior**

1. Policy re-check (`evaluate_action`).
2. Typed phrase validation when required.
3. **Manual-only / `api_execute_allowed:false`** → **`blocked`** if `dry_run:false`.
4. **`dry_run:true`** → success record, no subprocess.
5. Non–dry-run → allowlisted script resolution + `subprocess` (Windows only).

**Responses:** `RemediationExecution` dict (`result`: `dry_run` | `blocked` | `success` | `failure`).

**Failures:** `403` RBAC, `400` phrase / unknown action, `404` preview missing.

---

## GET `/platform/audit?limit=N`

**Purpose:** Recent **`PlatformAuditRecord`** tail.

**RBAC:** **`admin` or `security_auditor`**

**Response:** `{ "items": [ … ] }`

**Failures:** `403` viewer/operator.

---

## GET `/platform/metrics`

**Purpose:** Aggregated counters for dashboards + KPI signals under **`platform_signals.jsonl`**.

**RBAC:** viewer or higher (**headers recommended** — default missing role resolves to **`operator`**, which is allowed).

**Response fields (superset)**

| Field | Meaning |
|-------|---------|
| `endpoint_count` | Distinct endpoint ids in `endpoints.jsonl` |
| `open_failure_events` | `status == open` |
| `events_by_category` / `events_by_severity` | Histograms |
| `incident_cluster_count` | `cluster_failure_events()` over all events |
| `affected_endpoint_count` | Unique endpoints inside any cluster |
| `remediation_preview_count` | JSONL rows |
| `remediation_execution_count` | JSONL rows |
| `blocked_action_count` | Audit rows `decision==blocked` |
| `dry_run_execution_count` | Executions `result==dry_run` |
| `repair_success_rate` | `success / (success+failure)` executions (null when none) |
| `false_positive_rate` | `false_positive_events / events` |
| `proxy_changes_total` / `proxy_enable_transitions_total` | Derived from **`platform_signals.jsonl`** |
| `unknown_actor_events_total` | Unknown actor markers + boolean flags on signal rows |
| `attribution_confidence_avg` | Mean of `confidence` samples (signals + `attribution_records.jsonl`) |
| `rollback_preview_total` / `rollback_execute_total` / `rollback_blocked_total` | Signal kinds for rollback storytelling |
| `endpoint_heartbeat_total` | Counts `kind=heartbeat` rows (complements `endpoints.jsonl`) |
| `signals_file` | Resolved path for transparency |

**Failure modes:** empty files → zeros / null rates.

---

## GET `/platform/incidents?limit=N`

**Purpose:** Deterministic incident clusters over current `failure_events.jsonl`.

**RBAC:** viewer or higher.

**Response:** `{ "items": [IncidentCluster…], "total_candidates": <int> }`

---

## GET `/platform/attribution/{event_id}`

**Purpose:** Merge stored `FailureEvent` + optional `attribution_context.jsonl` bundle into an evidence list with `attribution_level` + `confidence`.

**RBAC:** **`operator`**, **`admin`**, or **`security_auditor`**.

**Side effects:** Appends **`attribution_records.jsonl`** (and audits `attribution_resolve`) when `persist` query param is true (**default**).

---

## Integration notes

- **CORS:** `backend.main` permits `*` for demo — tighten for real deployments.
- **Auth bypass:** JWT paths on other routes unaffected; **`/platform/*`** uses header RBAC-lite only unless you add wrappers.
- **Operator vs admin ergonomics:** default missing header ⇒ **`operator`** — give **`admin`** to exercise live repair + audit comfortably.

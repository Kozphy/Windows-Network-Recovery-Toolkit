# Platform API contract (`/platform/*`)

Local-first FastAPI routes mounted from `backend/platform_routes.py`. Authentication is **header-based mock RBAC** for portfolio demos — not production IdP integration.

**Headers**

| Header | Purpose |
|--------|---------|
| `X-Operator-Id` | Actor id in audit rows |
| `X-Operator-Role` | `viewer` \| `operator` \| `admin` \| `security` |
| `X-Request-Id` | Optional correlation (client-generated) |

---

## GET `/platform/health`

**Purpose:** Liveness + safe-mode / dry-run defaults.

**Request**

```http
GET /platform/health HTTP/1.1
Host: 127.0.0.1:8000
```

**Response example**

```json
{
  "status": "ok",
  "safe_mode": true,
  "remediation_default": "dry_run",
  "platform_data_dir": "/tmp/wrt-platform-demo"
}
```

**Safety:** Read-only. **Audit:** None.

---

## POST `/platform/diagnosis/run`

**Purpose:** Run read-only diagnosis pipeline and persist replayable run.

**Request example**

```http
POST /platform/diagnosis/run HTTP/1.1
X-Operator-Role: operator
Content-Type: application/json

{"endpoint_id": "demo-ep", "include_live_probes": false}
```

**Response example**

```json
{
  "run_id": "run_abc123",
  "endpoint_id": "demo-ep",
  "observations": [],
  "policy_decision": "PREVIEW"
}
```

**Safety:** `include_live_probes=false` avoids live host probes in demos. **Dry-run:** N/A (no remediation). **Audit:** Diagnosis run appended to product contract store.

---

## POST `/platform/remediation/preview`

**Purpose:** Policy-gated preview of an allowlisted action.

**Request example**

```json
{
  "endpoint_id": "demo-ep",
  "failure_event_id": "ev-1",
  "requested_action": "reset_dns",
  "surface": "api"
}
```

**Response example**

```json
{
  "preview_id": "uuid",
  "proposed_action": "reset_dns",
  "allowed_by_policy": true,
  "requires_typed_confirmation": true,
  "confirmation_phrase": "RUN_DNS_RESET",
  "dry_run": true,
  "audit_event_id": "..."
}
```

**Safety:** Viewer denied (403). Shell injection in action name → 400. **Dry-run:** Response marks preview as non-mutating. **Audit:** `remediation_preview` row + `remediation_previews.jsonl`.

---

## POST `/platform/remediation/execute`

**Purpose:** Execute or dry-run a previously stored preview.

**Request example**

```json
{
  "preview_id": "uuid",
  "confirmation_phrase": "RUN_DNS_RESET"
}
```

Omitting `dry_run` defaults to **`true`**.

**Response example (dry-run)**

```json
{
  "result": "dry_run",
  "dry_run": true,
  "stdout_redacted": "[dry-run] no subprocess"
}
```

**Response example (blocked)**

```json
{
  "result": "blocked",
  "dry_run": false
}
```

**Safety:** Operator + `dry_run=false` → 403. Forbidden/high/manual actions → `blocked`. Allowlisted `.bat` only when admin + confirmation + env gates pass. **Audit:** Every attempt logged to `remediation_executions.jsonl` + audit JSONL.

---

## GET `/platform/replay/{run_id}`

**Purpose:** Replay stored diagnosis observations — **no live reprobe**.

**Request**

```http
GET /platform/replay/run_abc123 HTTP/1.1
X-Operator-Role: viewer
```

**Response example**

```json
{
  "run_id": "run_abc123",
  "replay_mode": "read_only",
  "observations": [],
  "policy_decision": "PREVIEW"
}
```

**Safety:** Read-only. **Audit:** None (read path).

Related: `POST /platform/replay/preview` accepts inline event arrays for policy drift analysis.

---

## GET `/platform/audit`

**Purpose:** Recent audit rows (RBAC: admin or security auditor).

**Response example**

```json
{
  "items": [
    {
      "audit_id": "...",
      "actor": "demo",
      "action": "remediation_preview",
      "decision": "allowed",
      "timestamp": "2026-06-04T12:00:00+00:00"
    }
  ]
}
```

**Safety:** Read-only. **Audit:** Reads existing append-only file — does not write.

---

## GET `/platform/metrics`

**Purpose:** JSONL-derived KPI counters for dashboard demos.

**Response example**

```json
{
  "proxy_changes_total": 0,
  "incident_cluster_count": 0,
  "unsafe_action_block_count": 0
}
```

**Safety:** Read-only. See [metrics.md](metrics.md) for field definitions.

---

## Error shape

FastAPI returns standard HTTP errors:

```json
{"detail": "viewer is read-only"}
```

Structured product contract errors may include `decision`, `reason`, and `audit_event_id` on remediation routes.

---

## Related

- [safety_model.md](safety_model.md)
- [policy_engine.md](policy_engine.md)
- Legacy SaaS/JWT routes: `backend/main.py` (de-emphasized)

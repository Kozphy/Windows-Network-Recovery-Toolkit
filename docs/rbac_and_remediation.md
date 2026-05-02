# RBAC and remediation gates (portfolio prototype)

## Headers

All **`/platform`** JSONL writes (except **`GET /platform/health`**) SHOULD include demo headers parsed by **`platform_core.rbac.parse_demo_principal`**:

- **`X-Operator-Id`** — pseudonymous operator label.
- **`X-Operator-Role`** — **`viewer`** | **`operator`** | **`admin`** | **`security`** (aliases to security auditor semantics).

Absent header defaults (**`operator`** / **`anonymous`**) preserve backward-compatible pytest and local demos—not an enterprise IdP stance.

## Role capabilities

| Role | Read scopes | Mutation |
| --- | --- | --- |
| **viewer** | Health, **`GET /platform/metrics`**, **`GET /platform/incidents`**, normalized **`GET /platform/events`** | **Forbidden** ingestion + remediation previews. |
| **operator** | Viewer reads + remediation **preview** + **`GET /platform/attribution/*`** | May **dry-run** **`POST /platform/remediation/execute`** only (**no live** repairs). Agent ingestion (**heartbeat**/snapshots/events) permitted. |
| **admin** | Operator reads + **`GET /platform/audit`** | Live execution for **registry allowlisted**, **policy-approved**, **LOW/MEDIUM** repair definitions when confirmations match — still **blocked** when registry marks **`manual_only`**, **`high`**, or **`forbidden`**. |
| **security** (`security` header) | **Audit trails** (`GET /platform/audit`) + **attribution payloads** (**`GET /platform/attribution/*`**) — same read posture as auditors | **Forbidden** ingestion and remediation preview/execute (read-focused operator). |

## Policy + registry interplay

Remediation actions resolve exclusively through **`platform_core.remediation_registry`**. **`POST /platform/remediation/preview`** must reject shell injection-shaped action strings (**`policy.is_shell_injection`**).

**Firewall reset** surfaces as **`firewall_reset_manual_only`** (**`high`** / **`manual_only`**) → **API execution permanently blocked**, preview may still describe operator runbooks depending on **`evaluate_action`**.

**Adapter disable patterns** resolve to **`adapter_disable_forbidden`** → **explicitly forbidden**.

## Mandatory audit + dry-run

Every preview/execute path appends **`platform_data/remediation_previews.jsonl`** / **`remediation_executions.jsonl`** and mirrors operator intent into **`platform_data/audit.jsonl`** through **`platform_core.audit.write_audit`**.

Dry-run executions remain first-class (**`result=dry_run`**) suitable for Grafana-style success-rate denominators later.

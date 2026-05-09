# Proxy remediation contract

This document is the single source of truth for the typed-confirmation gate, allowlisted state-changing actions, Last Known Good (LKG) snapshot rules, post-change validation, and audit JSONL emitted by the WinINET proxy remediation surfaces.

## Scope

Applies to:

- CLI: `python -m src proxy disable`, `python -m src proxy restore-lkg`, the legacy `python -m src proxy-disable`, and the snapshot tooling under `python -m src proxy-snapshot ...`.
- Backend: `POST /api/proxy/disable-preview`, `POST /api/proxy/disable`, `POST /api/proxy/restore-lkg`, `POST /api/proxy/config-check`, `POST /api/proxy/registry-writer-proof`.

Out of scope (always blocked from this contract): firewall reset, adapter disable / reset, Winsock reset, process kill, certificate deletion, broad registry cleanup, arbitrary shell.

## Default posture

| Surface | Default posture |
| --- | --- |
| `disable-preview` / `proxy disable` | Preview only — dry-run (`mutated=false`). |
| `proxy disable --dry-run false` (no confirmation) | `BLOCK` with reason `missing_confirmation`. |
| `proxy disable --dry-run false --confirm <wrong>` | `BLOCK` with reason `confirmation_mismatch`. |
| `proxy disable --dry-run false --confirm DISABLE_WININET_PROXY` | May mutate `ProxyEnable` (and optionally `ProxyServer` via `--clear-server`) only after capturing an LKG snapshot. |
| `proxy restore-lkg` | Preview only by default; live restore requires `RESTORE_WININET_PROXY_FROM_LKG` and an existing LKG row. |
| `proxy config-check`, `proxy registry-writer-proof` | Read-only always; emit audit rows in `logs/safety_audit.jsonl`. |

## Allowlisted state-changing actions

| `action_id` | Confirmation phrase | Allowed registry fields | Risk | Reversible |
| --- | --- | --- | --- | --- |
| `disable_wininet_proxy` | `DISABLE_WININET_PROXY` | `ProxyEnable` (+ optional `ProxyServer`) | medium | yes (LKG) |
| `restore_wininet_proxy_from_lkg` | `RESTORE_WININET_PROXY_FROM_LKG` | `ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `ProxyOverride`, `AutoDetect` | medium | yes (previous snapshot) |

Any action_id not in the allowlist is blocked with `unknown_action`. Actions marked `blocked` in `src/proxy_guard/remediation.py::_ALLOWLIST` (firewall_reset, disable_adapter, kill_process, delete_certificate, broad_registry_cleanup) are blocked even with confirmation.

## Structured response shape

Both the `disable` and `restore-lkg` endpoints return the same shape:

```json
{
  "action_id": "disable_wininet_proxy | restore_wininet_proxy_from_lkg",
  "decision": "ALLOW | PREVIEW | BLOCK",
  "dry_run": true,
  "mutated": false,
  "reason": "...",
  "audit_event_id": "...",
  "before": { "...": "..." },
  "after": null,
  "action": {
    "action_id": "...",
    "required_confirmation": "...",
    "allowed_registry_fields": ["..."]
  },
  "planned_action": {
    "human": ["..."],
    "mutation_argv": [["reg", "add", "..."]],
    "requested_registry_fields": ["..."]
  }
}
```

`audit_event_id` always references an append-only row in either `logs/repair_audit.jsonl` (proxy disable) or `logs/safety_audit.jsonl` (restore-lkg, config-check, registry-writer-proof, agent next-step).

## Last Known Good (LKG) snapshot

Before any confirmed mutation:

1. The CLI captures the current HKCU WinINET tuple via `capture_wininet_snapshot`.
2. The capture is appended to `logs/proxy_snapshots.jsonl` (transient rollback) with a `snapshot_id`.
3. Operators can additionally name a stable LKG via `python -m src proxy-snapshot save --name <label>` which writes `logs/proxy_known_good_snapshots.jsonl`.
4. `python -m src proxy restore-lkg` reads the youngest row (or `--name <label>`) and proposes only the WinINET fields documented above.
5. If no snapshot exists, restore is blocked with `no_lkg_snapshot_available` (no implicit "last known good" is fabricated).
6. WinHTTP, Git, npm, environment variables, browser policies, firewall rules, certificates, and processes are intentionally untouched by `proxy restore-lkg`.

## Post-change validation

After a successful `proxy disable` mutation, the CLI immediately runs read-only validation:

- Re-reads HKCU `ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `ProxyOverride`.
- Probes DNS, TCP 443, and HTTPS direct.
- Optionally runs an HTTPS HEAD against a target URL (e.g. LinkedIn) when `curl.exe` is available; the probe is skipped without failing the run when unavailable.
- Writes a `post_change_validation` audit row, including `verification_result` and `repair_effect`.

Validation failure does **not** trigger broad automatic repair. The operator decides whether to roll back via `proxy restore-lkg`.

## Audit JSONL

Every preview, block, execute attempt, and validation result is recorded as a single JSONL line. The schema includes:

```json
{
  "audit_event_id": "uuid",
  "timestamp": "...",
  "event_kind": "diagnosis_run | proof_run | remediation_preview_requested | remediation_execute_requested | remediation_blocked_missing_confirmation | remediation_blocked_wrong_confirmation | remediation_blocked_disallowed_action | remediation_success | remediation_failed | post_change_validation_started | post_change_validation_completed | lkg_snapshot_created | lkg_restore_preview_requested | lkg_restore_executed | agent_next_step_requested",
  "action_id": "...",
  "decision": "ALLOW | PREVIEW | BLOCK",
  "dry_run": true,
  "mutated": false,
  "reason": "...",
  "before_summary": { "...": "..." },
  "after_summary": { "...": "..." },
  "validation_summary": { "...": "..." }
}
```

Constraints:

- Append-only. Old rows are never overwritten.
- Failed attempts and missing/wrong confirmation rows are always written.
- Sensitive environment dumps and credentials are never serialized.
- `audit_event_id` is included in the response so operators can correlate API responses with audit rows.

# Reliability event model v2 (`schema_version: "2.0"`)

## Why v2 exists

Legacy JSONL audits (especially `logs/repair_audit.jsonl`) centred on **“what command ran?”** Successful `reg.exe` exit codes prove **repair command success**, not **endpoint reliability success**.

Repeated cases where HKCU proxy is disabled and later re-enabled are **reliability incidents**. They require:

1. Observable **system state** (snapshots).
2. **Repair attempts** (planned argv + subprocess results).
3. **Verification** that state matches expectation after repair.
4. **Drift** when state regresses toward a bad configuration later.
5. **Attribution** that maps loopback listeners to processes **without over-claiming** registry authorship.

## Repair success versus reliability success

| Question | Typical v1 artefact | v2 artefact |
|----------|---------------------|-------------|
| Did `reg add` succeed? | `repair_audit.jsonl` `results[].code == 0` | `repair_attempt.result.command_success` |
| Is ProxyEnable actually 0 after repair? | `verification_result.ok` embedded in v1 row | `verification` event |
| Did the machine **stay** fixed? | (not modeled) | `drift_detected` comparing previous known-good vs current |

**Design language:** prefer “did the system **stay** repaired?” over “did the repair command succeed?”

## JSONL sinks (append-only)

All under `logs/` at the toolkit repo root:

| File | Contents |
|------|----------|
| `snapshots.jsonl` | `snapshot` rows (WinINET HKCU observations + parsed proxy fields). |
| `repairs.jsonl` | `repair_attempt` rows (argv, confirmation policy, subprocess result). |
| `verifications.jsonl` | `verification` rows (expected vs observed, ok, confidence). |
| `drifts.jsonl` | `drift_detected` rows (baseline vs current proxy enablement/value). |
| `attribution.jsonl` | `attribution` rows (listener/process hints + explicit limits text). |
| `incidents.jsonl` | `incident_summary` rows (rollup counters and recommended next actions). |

Each row MUST include:

```json
{
  "schema_version": "2.0",
  "event_type": "<type>",
  "event_id": "<uuid>",
  "timestamp_utc": "<iso8601 utc>",
  "incident_id": "<uuid deterministic from proxy>",
  "correlation_key": "<truncated sha256-ish cluster id>"
}
```

### Common field semantics

- **`incident_id`**: deterministic `uuid5` derived from canonical `ProxyServer` string (`src.network_state.event_log.incident_id_from_proxy`).
- **`correlation_key`**: stable short hash for dashboards (`correlation_key` helper).
- **Cross-links**: `repair_attempt.snapshot_event_id` references preceding `snapshot.event_id`; `verification.repair_event_id` ties back to primary repair attempts.

### Drift (`drift_detected`)

Raised when a prior **disabled / known-good baseline** diverges—for example **`ProxyEnable: 0 → 1`** after tooling or policy rewrote HKCU WinINET keys.

Severity rule:

- `repeat_count >= 3` ⇒ `severity = "high"`.
- otherwise `severity = "medium"` (explicitly enumerated in helpers).

Counters on repeated proxy re-enable are tracked per `correlation_key` in `logs/drifts.jsonl`; `repeat_count` is the ordinal of the matching drift for that correlation cluster.

### Attribution limits

Rows include a non-empty **`limits`** list:

- Listening on the proxy port establishes **association**, not causal proof of HKCU mutations.
- Do **not** label a process malicious without independent evidence.

## Producer integration

- **`python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY`**: after typed confirmation (non-dry-run), emits `snapshot`, per-mutation `repair_attempt`, `verification`, and merges an `incident_summary` beside the legacy `repair_audit.jsonl` append.
- **`python -m src proxy-watch`**: on substantive transitions, emits v2 **`attribution`** when a localhost port parses, and **`drift_detected` + incident_summary rollup** when `proxy_enable` moves from disabled (`0`) to enabled (`1`).

Legacy watchers (`logs/proxy_guard*.jsonl`) remain unchanged.

## Migrating legacy repair audits

The repo ships `tools/migrate_v1_audit_to_v2.py`. It reads `logs/repair_audit.jsonl` and writes **cloned** NDJSON outputs under **`logs/v2_migrated/`** without modifying originals.

Converted rows carry optional `_migrated_from` annotations for lineage.

Example:

```bash
python tools/migrate_v1_audit_to_v2.py --repo .
```

Outputs:

- `logs/v2_migrated/snapshots.jsonl`
- `logs/v2_migrated/repairs.jsonl`
- `logs/v2_migrated/verifications.jsonl`
- plus empty sinks routed if unused (`drifts`, `attribution`, `incidents`, `unclassified`) when only minimal rows exist.

Unrecognized legacy rows synthesize `migration_skip` entries in `logs/v2_migrated/unclassified.jsonl` (never destroys source data).

## Tests

Pytest exercises parsing, hashing stability, NDJSON schemas, drift severity, and migration idempotency on originals:

```bash
python -m pytest tests/test_event_model_v2.py -v
```

## Python API sketch

Prefer importing from `src.network_state.event_log`:

- `log_snapshot`, `log_repair_attempt`, `log_verification`, `log_drift`, `log_attribution`
- `update_or_write_incident_summary`
- `parse_proxy`, `correlation_key`, `incident_id_from_proxy`

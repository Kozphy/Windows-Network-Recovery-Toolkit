# Proxy Guard — LKG rollback semantics

Automated remediation now restores **`reports/proxy_guard_lkg.json`** (Last Known Good) instead of
blindly clearing proxy settings whenever policy blocks an observed change **and**
`--auto-rollback` is enabled.

## Operational contract

| Flag / state | Behaviour |
| --- | --- |
| Default (no `--auto-rollback`) | Observe + JSONL audits only (`rollback_plan.restore_*` may still be true for planning telemetry). |
| `--auto-rollback` | When policy returns `blocked`, attempt HKCU regeneration from LKG snapshots. WinHTTP restores only execute when WinHTTP telemetry was captured explicitly in the snapshot. |
| `--dry-run` **or** `--dry-run-rollback` | Executes the rollback **preview** pathway (logged argv / synthetic rows) — **no** live HKCU or `netsh` writes. |

## Capturing baseline

- **`--trust-current`**: on the initial poll, persists the freshly captured composite snapshot (`ProxySnapshot`) to `reports/proxy_guard_lkg.json`.
- **`--show-lkg`**: prints JSON and exits (read-only helper).
- **`--clear-lkg`**: deletes the file and exits — use only when coordinating with ops.

## What is intentionally out of scope (still)

Git / npm global config and per-user proxy environment strings are modeled in snapshots for diagnostics,
but **live restoration requires `--restore-git-npm-env` AND** is currently blocked inside
`execute_lkg_snapshot_rollback` until an explicit operator confirmation workflow ships.

## Recovery

1. Fix the modifying software or policy source.
2. Replace LKG by rerunning `proxy-guard --trust-current` from a known-good console session.
3. Manually restore corporate PAC / WinHTTP policy if IT mandates separate tooling beyond User WinINET snapshots.


# Operator Runbook

## Proxy drift incident

1. `python -m toolkit replay proxy_drift_incident.jsonl`
2. Confirm tier < FINAL_CAUSATION → preview only
3. Collect Sysmon E13 if upgrading proof

## Unknown local proxy

1. Correlate listener owner — not writer proof
2. Policy: PREVIEW_ONLY or BLOCK destructive

## Correlation-only case

Never approve `disable_wininet_proxy` without writer telemetry.

## Proven registry writer

Require lineage + path validation before FINAL_CAUSATION.

## Rollback

Use `RESTORE_WININET_PROXY_FROM_LKG` with typed confirmation after snapshot.

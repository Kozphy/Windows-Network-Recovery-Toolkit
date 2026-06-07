# Operator safety

Guidance for running this toolkit safely on real endpoints.

## Before you run

1. Prefer read-only commands first (`diagnose`, `proxy-guard` preview paths, `/platform/diagnosis/run`).
2. Review policy output and `required_confirmation` before any execute path.
3. Do not paste live logs into public issue trackers without redaction.

## Execute paths

- **Default:** dry-run — no subprocess repair, no registry mutation.
- **Live execute:** requires allowlisted action, RBAC role, typed confirmation, and Windows where applicable.
- **Blocked forever at API:** process kill, firewall reset, adapter disable, arbitrary shell.

## Telemetry imports

Sysmon/EventLog/ETW fixtures improve **writer evidence quality** but do not authorize destructive actions. Treat `WRITER_AND_LISTENER_MATCH` as stronger correlation, not intent proof.

## When things look malicious

This tool **does not** remove malware or kill suspicious processes. Preserve JSONL audits, export telemetry fixtures, and escalate through your organization's security workflow.

## Recovery discipline

After remediation preview, verify stickiness with soak windows documented in proxy guard workflows. Re-open incidents when proxy re-enables after soak (`incident_engine` rules).

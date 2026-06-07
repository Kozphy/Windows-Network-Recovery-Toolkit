# Security boundaries

This platform is a **local-first diagnostic and remediation-preview** system. These boundaries define what the codebase will and will not do.

## In scope

- Read-only network/proxy/registry observation
- Hypothesis ranking with explicit evidence levels
- Policy-gated remediation **preview**
- Typed-confirmation execute paths for allowlisted actions
- Append-only audit and deterministic replay from stored observations
- Optional telemetry fusion (Sysmon/EventLog/ETW fixtures)

## Out of scope (non-goals)

- Antivirus or malware removal
- EDR-style autonomous containment
- Silent process termination
- Silent firewall reset or adapter disable
- Registry mutation without operator confirmation
- Proof of compromise without appropriate telemetry
- Default cloud upload of endpoint data

## Control surfaces

| Control | Implementation |
|---------|------------------|
| Dry-run default | API `ExecuteIn.dry_run=True`; tests enforce |
| Typed confirmation | Registry allowlist + confirmation phrases |
| No arbitrary shell | Policy rejects injection patterns |
| Evidence levels | Telemetry fusion ladder; listener ≠ writer proof |
| Append-only audit | JSONL sinks; no silent overwrites |
| Local-first storage | `platform_data/` gitignored; opt-in agent POST |

## API trust model

RBAC headers (`X-Operator-*`) are **unsigned demo simulation**. Do not treat them as production authentication.

See also [threat_model.md](threat_model.md), [operator_safety.md](operator_safety.md), and [abuse_cases.md](abuse_cases.md).

# Threat model

Local-first Endpoint Reliability Platform — design constraints for portfolio and lab use.

## Assets

| Asset | Description |
|-------|-------------|
| Endpoint state | Registry/proxy snapshots, diagnoses, fleet heartbeats |
| Audit JSONL | Append-only decision and remediation history |
| Operator trust | Policy/confirmation UX |
| Privacy | Hostnames, paths, proxy ports (redact before sharing) |

## Attacker model

| Actor | Capability | Goal |
|-------|------------|------|
| Malicious local process | Mutate HKCU proxy keys, bind localhost port | Redirect traffic |
| Compromised browser path | Fail HTTPS while network probes pass | Hide exfil path |
| Malicious listener | Own port without writing registry | Mislead attribution |
| Abused API caller | POST execute with crafted action | Force destructive repair |
| Confused operator | Skip preview | Apply wrong fix |
| Stale telemetry | Supply outdated Sysmon export | False writer match |

## Threats and mitigations

| Threat | Mitigation |
|--------|------------|
| Silent destructive repair | Dry-run default; policy BLOCK; typed confirmation |
| False accusation from listener correlation | Evidence ladder; ADR-004; fusion limitations |
| JSONL tampering | Hash-chain helpers; replay from stored observations |
| Credential leakage in logs | Redaction helpers; public-release audit script |
| Unsigned RBAC headers | Documented demo-only; not production auth |
| Critical incident from weak evidence | `incident_engine` caps severity |

## Non-goals

- Not antivirus or malware removal
- Not autonomous containment or EDR replacement
- Not guaranteed attribution without Sysmon/Procmon-class telemetry
- Not multi-tenant SaaS security in this repository
- Not trading, crypto, or financial decision-making (see `labs/`)
- Not generic AI agent decision-making (see `labs/decision_platform`)

## Controls summary

- Typed confirmation on mutation paths
- Registry allowlist
- No arbitrary shell from API
- Evidence levels (`NO_WRITER_EVIDENCE` … `WRITER_AND_LISTENER_MATCH`)
- Append-only audit
- Local-first storage (no default cloud upload)

See [security_boundaries.md](security_boundaries.md), [operator_safety.md](operator_safety.md), [abuse_cases.md](abuse_cases.md).

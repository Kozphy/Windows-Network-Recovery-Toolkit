# Threat model

Local-first **Endpoint Reliability Platform** — security observability and safe remediation boundaries.

## Assets

| Asset | Description |
|-------|-------------|
| Endpoint state | Registry/proxy snapshots, diagnoses, fleet heartbeats |
| Audit JSONL | Append-only decision and remediation history |
| Operator trust | Policy/confirmation UX |
| Privacy | Hostnames, paths, proxy ports (redact before sharing) |

## Threats

| Threat | Impact |
|--------|--------|
| Malicious local process modifies proxy settings | Browser/dev-tool traffic redirected; ping/DNS may still pass |
| Benign developer tool creates localhost proxy | False-positive attribution if treated as malware |
| Stale telemetry causes wrong attribution | Writer/listener mismatch; incorrect incident severity |
| Operator over-trusts heuristic evidence | Destructive or unnecessary remediation |
| Abused API caller attempts destructive remediation | Firewall reset, adapter disable, process kill |
| Logs accidentally include sensitive local data | Credential/path leakage in shared artifacts |

## Controls

| Control | Mechanism |
|---------|-----------|
| Local-first design | No default cloud upload; `PLATFORM_DATA_DIR` on disk |
| Synthetic fixtures in git | `tests/fixtures/demo/` — no real endpoint logs committed |
| Real logs ignored | `.gitignore` for `platform_data/`, `reports/`, machine exports |
| Evidence level separation | `OBSERVED_ONLY` → `FINAL_CAUSATION`; ordinal confidence |
| Sysmon/Procmon proof requirement | `PROVEN_REGISTRY_WRITER` requires writer telemetry class |
| Listener correlation is not proof | `CORRELATED` capped without upgrade guards |
| Typed confirmation | Registry mutation paths require explicit phrase |
| Dry-run default | API `execute` defaults `dry_run=true` |
| Append-only audit | Preview and execute attempts logged |
| Replayable decisions | Deterministic fixture replay + audit tail |
| Allowlist policy | Developer tooling and proxy hosts in `config/` |
| High-risk action blocking | `BLOCK_DESTRUCTIVE`, manual-only firewall paths |

## Attacker model

| Actor | Capability | Goal |
|-------|------------|------|
| Malicious local process | Mutate HKCU proxy keys, bind localhost port | Redirect traffic |
| Compromised browser path | Fail HTTPS while network probes pass | Hide exfil path |
| Malicious listener | Own port without writing registry | Mislead attribution |
| Abused API caller | POST execute with crafted action | Force destructive repair |
| Confused operator | Skip preview | Apply wrong fix |
| Stale telemetry | Supply outdated Sysmon export | False writer match |

## Explicitly out of scope

- Antivirus or malware removal
- Autonomous containment
- Enterprise EDR replacement
- Guaranteed attribution without Sysmon/Procmon-class telemetry
- Trading / financial decisions
- Generic AI agent decision-making
- Multi-tenant SaaS security in this repository

Experimental modules (decision intelligence, market events, edge device simulators) live under [`labs/`](../labs/README.md) and are **not** part of the main endpoint reliability threat boundary.

## Architecture diagram (trust boundaries)

```
┌─────────────────────────────────────────────────────────────┐
│  Operator / API client (untrusted input)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │ typed confirmation + dry_run default
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Policy engine (BLOCK / PREVIEW / REQUIRE_TYPED_CONFIRM)    │
└───────────────────────────┬─────────────────────────────────┘
                            │ allowed actions only
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Remediation preview (no silent kill / firewall / adapter)  │
└───────────────────────────┬─────────────────────────────────┘
                            │ append-only
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Audit JSONL + replay engine (local PLATFORM_DATA_DIR)      │
└─────────────────────────────────────────────────────────────┘
```

See also [security_boundaries.md](security_boundaries.md), [operator_safety.md](operator_safety.md), [evidence_model.md](evidence_model.md), [policy_model.md](policy_model.md).

# Case 004 — Reverter suspected

**Fixture:** `examples/evidence/REVERTER_SUSPECTED.json` · flapping `proxy_transitions` JSONL

## Symptom

Proxy settings flip repeatedly — user or process may be fighting automation.

## Evidence

- Rapid enable/disable transitions in JSONL replay
- Coalescing window merges sub-events
- State machine labels `REVERTER_SUSPECTED` when pattern matches

## Known / Not proven

| Known | Not proven |
|-------|------------|
| Configuration instability over time | Malicious reverter vs legitimate sync tool |
| Flapping loop in fixture replay | Identity of writer process without Sysmon E13 |

## Classification

- **Primary:** `REVERTER_SUSPECTED`
- **Secondary:** transition counts, timing signals
- **Proof tier:** T1–T2 without writer proof

## Control test

Stability control — FAIL on flapping beyond threshold.

## Policy

Preview-only; no kill-process or firewall actions.

## Human review

**Required** — accusatory-adjacent label; committee forum recommended.

## Audit artifact

`proxy-replay` output + hash-chained transition log.

## Governance value

Shows **temporal evidence** and human gate before narrative escalation.

## Limitations

Suspected reverter is not malware confirmation. Recommendation is not execution authority.

## Interview talking point

*"State machine + replay benchmark prove deterministic transitions — critical for audit reproduction."*

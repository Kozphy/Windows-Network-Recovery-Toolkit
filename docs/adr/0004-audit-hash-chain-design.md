# ADR-0004: Audit Hash Chain Design

## Status

Accepted

## Context

Technology risk committees and internal audit need tamper-evident decision logs. Plain JSONL files are editable without detection. Cryptographic complexity (PKI) may exceed local-first deployment constraints.

## Decision

Use **append-only SHA-256 hash chaining** per record:

- Body hash excludes `previous_hash`, `current_hash`, `signature_status`
- First record links from `genesis`
- `verify_chain()` recomputes and detects breaks at index
- Integrated into `governance-report` and `powerbi_star_export` integrity KPIs
- CTRL-010 formalizes verify procedure

Implementation: `src/platform_core/governance/chain_of_custody.py`, audit writer.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Unsigned JSONL only | No tamper detection |
| Full asymmetric signatures per record | Key management burden for local toolkit |
| Central database only | Conflicts with air-gapped / file-based audit export |

## Consequences

- Log deletion or reorder breaks chain — feature for integrity, ops burden for retention
- Verify pass required before attestation narrative in governance export
- Does not replace WORM storage or SIEM — complementary

## Security considerations

- Attacker with write access can append fraudulent records — chain detects **edit**, not **append forgery** without external anchor
- Recommend periodic copy to immutable storage for high-assurance environments

## Audit considerations

- Satisfies ITGC **integrity** questions for in-scope JSONL
- Does not satisfy **completeness** — off-tool actions out of scope
- Walkthrough: [audit-hash-chain-explained.md](../audit-hash-chain-explained.md)

## What this prevents

- Undetected modification of historical decision records
- Export of governance KPIs from tampered audit period without verify failure

## What this does not prove

- Truth of observations inside records
- Operator identity (no biometric signature)
- That all actions were logged

## Interview defense

"Verify answers: was the log tampered after write? It does not answer: was the investigation correct. I separate integrity from accuracy in every audit conversation."

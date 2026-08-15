# ADR-015: No silent kill; rewriter containment is policy-gated

## Status

Accepted — 2026-08-15

## Context

Operators facing recurring localhost WinINET rewrite (`127.0.0.1:<ephemeral>`) correlated with Session-0 persistence sometimes ask for `taskkill` of `node.exe`. `KILL_PROXY_PROCESS` is blocked in `windows_network_toolkit/safety.py`. A distinct operator-gated composite (`CONTAIN_LOCALHOST_REWRITER`) exists for scheduled-task + payload + Defender-exclusion containment.

Reviewers may conflate containment with EDR autonomous kill. See [0008-why-this-is-not-edr.md](0008-why-this-is-not-edr.md).

## Decision

1. Do **not** weaken `KILL_PROXY_PROCESS`. Silent or default process kill remains blocked.
2. Rewriter containment is **preview-default** and requires the typed token `CONTAIN_LOCALHOST_REWRITER`.
3. Match signals are **correlation** (task path, remote `iex`, exclusions) — not registry writer proof and not a malware verdict.
4. WNRT guardian / boot-trace tasks and `\Microsoft\Windows\*` tasks are never targeted.

## Consequences

- Operator incident card ranks `LOCALHOST_REWRITER_SUSPECTED` above dead-proxy so operators see containment preview first when persistence matches.
- Audit: `logs/rewriter_containment.jsonl`.
- Portfolio language must not say “we killed the attacker process.”

## What this does not prove

Writer identity, malware family, or that the endpoint is clean after containment.

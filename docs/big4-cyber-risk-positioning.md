# Big 4 cyber risk positioning

How to present this repository in **cyber risk**, **IT audit**, and **technology advisory** contexts.

---

## Problem framing

Enterprise endpoints fail in ways that look like "network outages" but are actually **misconfigured proxy state**. Traditional scripts fix symptoms without evidence, creating:

- Unaudited registry mutations
- False attribution (listener ≠ writer)
- Regulatory exposure when changes cannot be replayed

This platform treats proxy incidents as **risk decisions** with explicit uncertainty.

---

## Control themes

| Theme | Platform answer |
|-------|-----------------|
| **Identify** | 12-label classification + secondary signals |
| **Protect** | Block destructive actions by default |
| **Detect** | `proxy-watch`, reverter detection, timeline merge |
| **Respond** | Policy-gated `proxy-disable` with typed confirmation |
| **Recover** | Rollback snapshots + audit replay |
| **Govern** | `.audit/*.jsonl`, incident reports, limitations[] |

Cross-reference: [governance/control_mapping.md](governance/control_mapping.md)

---

## Evidence hierarchy (audit language)

1. **Observation** — registry and netstat reads
2. **Correlation** — listener/process match
3. **Proof** — structured contrast checks (`diagnose --proof`)
4. **Attribution** — Sysmon E13 registry writer (optional telemetry)

Never collapse these tiers in client-facing language.

---

## Golden case for workshops

**Dead localhost proxy 59081:**

- Symptom: browser fails, ping OK
- Classification: `DEAD_PROXY_CONFIG`
- Proof: supported (0.92)
- Remediation: WinINET disable only — **does not prove malware**

Workshop doc: [case-studies/dead-localhost-proxy.md](case-studies/dead-localhost-proxy.md)

---

## Risk register items (honest)

| Risk | Mitigation in platform | Residual |
|------|------------------------|----------|
| Wrong remediation | Dry-run default, typed tokens | Operator error |
| False MITM alert | ≥2 indicators required; limitations surfaced | Heuristic false positives |
| Reverter respawn | `proxy-watch` + `REVERTER_SUSPECTED` | Parent process may survive |
| Audit tampering | Append-only JSONL; hash chain in canonical path | Local disk access |

---

## Interview phrases

- "We **document what we cannot prove** in every classification and proof output."
- "Remediation is a **policy decision**, not a diagnostic side effect."
- "Audit trail is **append-only** and suitable for incident reconstruction."

Related: [interview-case-study.md](interview-case-study.md) · [production_readiness.md](production_readiness.md)

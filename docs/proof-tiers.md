# Proof Tiers (T0–T5)

**Normative ladder** for claim strength. Each tier adds evidence type—not authorization to accuse or remediate.

Modules: `src/platform_core/governance/proof_tier.py`, `windows_network_toolkit/evidence_schema.py`, `docs/proxy-proof-ladder.md` (detailed examples).

---

## Tier Definitions

| Tier | Name | Definition |
|------|------|------------|
| **T0** | Observation only | Unstructured or uncorroborated note |
| **T1** | Single deterministic signal | Structured WinINET/WinHTTP/PAC read |
| **T2** | Multiple independent signals | Config + listener + path contrast |
| **T3** | Reproducible state comparison | Direct vs proxied HTTPS/TCP probes |
| **T4** | Timeline-supported causal hypothesis | Registry writer telemetry (Sysmon E13) |
| **T5** | Confirmed reproducible chain + audit | Human-confirmed apply logged in hash chain |

**Rule:** Never skip rungs in audit narrative. Never describe T2 as T4.

---

## Remediation Permissions by Tier

| Tier | Preview remediation | Live registry apply | Destructive actions |
|------|--------------------|--------------------|---------------------|
| T0 | No | No | Block |
| T1 | Observe only | No | Block |
| T2 | Preview allowed | Requires confirmation | Block |
| T3 | Preview allowed | Requires confirmation + review | Block |
| T4 | Preview + typed confirm | Allowed for allowlisted actions | Block |
| T5 | Full audit trail | Human-approved apply logged | Still block kill/firewall/adapter |

Confidence is not certainty. Policy ALLOW/PREVIEW is not a safety guarantee.

---

## Mapping to Evidence Tiers

| Proof T0–T5 | Evidence tier (platform_core) |
|-------------|-------------------------------|
| T0–T1 | `OBSERVED_ONLY` |
| T2 | `CORRELATED` |
| T3 | `PROVEN_NETWORK_IMPACT` (partial) |
| T4 | `PROVEN_REGISTRY_WRITER` |
| T5 | `FINAL_CAUSATION` + governance audit |

Resolver: `src/platform_core/governance/proof_tier.py` · `map_proof_tier_to_evidence_tier()`

---

## CLI

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit tls-proof --fixture tests/fixtures/enert/tls_cert_mismatch.json
```

Tests: `tests/platform_core/governance/test_proof_tier_resolver.py`

*Detailed case narratives:* [proxy-proof-ladder.md](proxy-proof-ladder.md)

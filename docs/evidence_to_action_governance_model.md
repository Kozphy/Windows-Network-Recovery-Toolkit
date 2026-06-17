# Evidence-to-Action Governance Model

**Schema:** `evidence_to_action.v1`  
**Status:** Normative guidance for narrative, classification, and remediation outputs

---

## Executive Summary

The Windows Network Recovery Toolkit (Technology Risk & Control Analytics Platform) converts endpoint observations into **governed decisions** — not autonomous verdicts. The Evidence-to-Action Governance Model formalizes six epistemic principles that separate what we **observe**, what we **correlate**, what we **prove**, what we **classify**, what **policy permits**, and what **humans may execute**.

This model supports audit-ready workflows for IT Risk Advisory, SRE governance, Cyber/IT Risk, and Data/Risk analytics teams who need consistent language, evidence tiers, and remediation gates without conflating triage labels with accusations or recommendations with execution authority.

**Implementation:** `src/platform_core/governance/evidence_to_action.py` attaches an optional `governance` envelope to JSON outputs. Existing CLI commands and schemas remain backward compatible.

---

## The Six Principles

| # | Principle | Rule |
|---|-----------|------|
| 1 | **Observation is not proof** | Registry reads, netstat snapshots, and proxy state are observations until structured proof checks pass. |
| 2 | **Correlation is not causation** | Listener/process correlation does not prove registry-writer causation without writer telemetry (e.g., Sysmon E13). |
| 3 | **Confidence is not certainty** | Scores are ordinal/heuristic rankings — never statistical probabilities of compromise. |
| 4 | **Classification is not accusation** | Labels like `UNKNOWN_LOCAL_PROXY` or `POSSIBLE_MITM_RISK` are investigative triage — not malware or attacker verdicts. |
| 5 | **Policy permission is not safety guarantee** | `ALLOW` or `PREVIEW_ONLY` outcomes still require dry-run preview, typed confirmation, rollback plan, monitoring, and audit. |
| 6 | **Recommendation is not execution authority** | Remediation previews and policy recommendations do not authorize autonomous registry mutation, process kill, or destructive actions. |

---

## Worked Examples

### WinINET proxy drift (`DEAD_PROXY_CONFIG`)

**Observation:** WinINET `ProxyServer` points to `127.0.0.1:59081`; WinHTTP may use direct access.  
**Proof:** Listener check fails — configured localhost port has no bound process. Conclusion: `supported` for dead proxy path.  
**Classification:** `DEAD_PROXY_CONFIG` — reliability finding, not security verdict.  
**Governance:** `claim_strength: proof`, `causal_language_allowed: false`, `execution_authority: preview_only`.

**Allowed:** "Evidence is consistent with a dead WinINET localhost proxy blocking browser traffic."  
**Prohibited:** "Caused by malware" or "attacker modified the registry."

### Unknown localhost proxy (`UNKNOWN_LOCAL_PROXY`)

**Observation:** Localhost proxy port has a listener; process attribution may be incomplete.  
**Correlation:** Process name may correlate with the port — not proof of who wrote WinINET settings.  
**Classification:** `UNKNOWN_LOCAL_PROXY` — requires further attribution.  
**Governance:** `classification_is_accusation: false` always; narrative must not claim compromise.

**Allowed:** "Listener correlated with process X; requires further attribution for registry writer."  
**Prohibited:** "Compromised endpoint" or "proved malware."

### TLS certificate mismatch (`POSSIBLE_MITM_RISK`)

**Observation:** Browser TLS chain differs from direct `curl` path or expected issuer.  
**Correlation:** Path divergence supports a **hypothesis** of interception or misconfiguration — not confirmed MITM.  
**Classification:** `POSSIBLE_MITM_RISK` — security-adjacent triage label.  
**Governance:** Low/medium tiers block "confirmed MITM" language.

**Allowed:** "Possible MITM risk — path mismatch supports further investigation."  
**Prohibited:** "Confirmed MITM" or "proves interception" without `FINAL_CAUSATION` tier.

### Remediation preview (`proxy-disable --dry-run`)

**Recommendation:** Disable WinINET proxy, clear `ProxyServer`, capture rollback snapshot.  
**Policy:** `PREVIEW_ONLY` by default; typed confirmation `DISABLE_WININET_PROXY` required to apply.  
**Governance:** `execution_authority: preview_only` until human supplies confirmation phrase.

**Allowed:** "Preview only — requires typed confirmation before registry mutation."  
**Prohibited:** "Safe to execute automatically."

---

## Allowed vs Prohibited Language

| Context | Allowed (default tiers) | Prohibited unless evidence tier is high enough |
|---------|-------------------------|------------------------------------------------|
| Causation | "evidence is consistent with…", "correlated with…", "supports the hypothesis…" | "caused by…", "root cause confirmed…" |
| Attribution | "requires further attribution…", "listener correlated with…" | "attacker…", "compromised…" |
| Security labels | "possible MITM risk…", `POSSIBLE_MITM_RISK` as triage | "confirmed MITM", "proves interception" |
| Malware | "does not prove malware" (explicit negation) | "proved malware", "malware confirmed" |
| Confidence | "ordinal confidence 0.92 (not probability)" | "% chance", "probability of compromise" |
| Execution | "preview only", "human approval required" | "safe to execute automatically" |

**High enough tiers for causal language:** `attribution`, `final_causation` (see evidence tier mapping). Even at high tiers, classifications remain non-accusatory.

---

## Evidence Tier Mapping

| Tier | `claim_strength` | Causal language | Typical sources |
|------|------------------|-----------------|-----------------|
| `OBSERVED_ONLY` | `observation` | No | Registry read, proxy state snapshot |
| `CORRELATED` | `correlation` | No | Listener ↔ port, process name match |
| `PROVEN_REGISTRY_WRITER` | `proof` | No* | Sysmon E13 / writer telemetry |
| `FINAL_CAUSATION` | `final_causation` | Yes (bounded) | Writer + port/network impact proof |
| Proof conclusion `supported` | `proof` | No | Structured proof engine pass |

\*Writer proof establishes **who changed settings**, not malicious intent.

---

## Policy / Action Mapping

| Policy outcome | `execution_authority` | Required controls |
|----------------|----------------------|-------------------|
| `PREVIEW_ONLY` / dry-run | `preview_only` | Dry-run default, audit log |
| `ALLOW` (unexecuted) | `human_required` | Typed confirmation, rollback plan |
| `ALLOW` + confirmation + apply | `human_required` | Snapshot, verification, audit |
| `BLOCK` / `DENY` | `blocked` | No mutation |
| Destructive actions (kill, firewall reset, adapter disable) | `blocked` | Never in default policy matrix |

---

## Stakeholder Alignment

### Big 4 Risk Advisory

Provides **management-ready** artifacts (`risk-assess`, `governance-report`) with explicit limitations, control test results, and non-accusatory classifications — aligned with ITGC themes (change management, monitoring, remediation governance).

### SRE / Platform Governance

Supports **dry-run-first** remediation, deterministic replay, and KPIs via `analytics-summary` (preview vs execute rates, hash-chain integrity) without treating heuristics as blocking verdicts.

### Cyber / IT Risk

Bridges operational reliability (`DEAD_PROXY_CONFIG`) and security-adjacent triage (`POSSIBLE_MITM_RISK`, `UNKNOWN_LOCAL_PROXY`) with evidence tiers that refuse automatic escalation to compromise language.

### Data / Risk Analytics

Warehouse-friendly JSON (`governance` envelope, ordinal `confidence_type`) enables SQL dashboards on classification distribution, evidence tiers, and policy outcomes without misreading scores as probabilities.

---

## JSON Governance Envelope

Optional nested field on decision outputs (backward compatible):

```json
{
  "governance": {
    "governance_model": "evidence_to_action.v1",
    "claim_strength": "proof",
    "confidence_type": "ordinal_not_probability",
    "causal_language_allowed": false,
    "classification_is_accusation": false,
    "execution_authority": "preview_only",
    "limitations": [
      "Observation is not proof; correlation is not causation.",
      "DEAD_PROXY_CONFIG is an investigative label — not a confirmed threat verdict."
    ]
  }
}
```

---

## Limitations

- Governance envelopes are **declarative** — they do not replace human review or organizational policy.
- Heuristic classifications can be wrong; the model prevents **overclaim**, not **under-investigation**.
- Writer telemetry (Sysmon E13) may be unavailable on many endpoints; correlation ceilings remain in force.
- The platform is **not** EDR, antivirus, or SOAR — it does not replace dedicated security products.
- Markdown reports summarize JSON governance fields but may not expose every nested limitation.

---

## Related Documentation

- [Control matrix](control-matrix.md)
- [README Big 4 portfolio](README_BIG4_PORTFOLIO.md)
- [Analytics data model](analytics_data_model.md)
- Principles config: `src/platform_core/principles/principles.yaml`

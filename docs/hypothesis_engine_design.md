# Hypothesis Engine Design — Security Detection Engineering

**Status:** Design + reference implementation  
**Module:** `src/platform_core/hypothesis/`  
**Audience:** Detection engineers, incident responders, platform engineers

---

## 1. Purpose

The Hypothesis Engine transforms **four evidence domains** into **competing, cited hypotheses** suitable for endpoint investigation — without claiming certainty or autonomous action.

### Inputs

| Domain | Examples |
|--------|----------|
| **Registry** | ProxyEnable, ProxyServer, WinHTTP direct, Sysmon E13 writer |
| **Process** | Listener PID, process name, signature, known-dev allowlist |
| **Timeline** | Ordered signals (proxy drift → browser fail → direct path OK) |
| **Network** | DNS, ping, browser HTTPS, direct vs proxied path, TLS, VPN |

### Outputs (per hypothesis)

| Field | Description |
|-------|-------------|
| **Hypothesis** | Cautious explanation — not a verdict |
| **Confidence** | Ordinal 0.10–0.98 (capped) |
| **Supporting Evidence** | Cited refs with tier + observation/proof flag |
| **Missing Evidence** | What would strengthen or weaken the claim |
| **Alternative Explanations** | Competing hypothesis titles (mandatory) |
| **Recommended Actions** | Preview/investigate only — policy-gated |

### Rules enforced in code

1. Never claim certainty (`confidence ≤ 0.98`, disclaimers required)
2. Always provide competing hypotheses (`alternatives[]` + `alternative_explanations[]`)
3. Separate observation from proof (`EvidenceRef.tier`, `is_proof`)
4. Explain confidence score (`confidence_explanation`)

---

## 2. Data structures

```python
# src/platform_core/hypothesis/models.py

class EvidenceRef(BaseModel):
    evidence_id: str
    kind: EvidenceKind          # registry | process | timeline | network
    signal: str
    tier: EvidenceTierName      # OBSERVED_ONLY … FINAL_CAUSATION
    observed_value: str
    summary: str
    is_proof: bool              # True only for proof-tier network/registry evidence

class MultievidenceInput(BaseModel):
    incident_id: str
    registry: RegistryEvidence | None
    process: ProcessEvidence | None
    timeline: TimelineEvidence | None
    network: NetworkEvidence | None

class HypothesisEvaluation(BaseModel):
    hypothesis_id: str
    title: str
    hypothesis: str
    confidence: float           # ordinal, max 0.98
    confidence_rank: Literal["low", "medium", "high"]
    confidence_display: str     # "ordinal 0.87 (heuristic rank, not probability or certainty)"
    confidence_explanation: str
    supporting_evidence: list[EvidenceRef]
    missing_evidence: list[str]
    alternative_explanations: list[str]
    recommended_actions: list[str]
    limitations: list[str]
    incident_type: str

class HypothesisEngineResult(BaseModel):
    incident_id: str
    primary: HypothesisEvaluation
    alternatives: list[HypothesisEvaluation]   # min 1, target 2–4
    epistemic_notice: str
```

---

## 3. Algorithms

### 3.1 Pipeline

```text
MultievidenceInput
  → build_signal_map()           # boolean feature vector across domains
  → collect_evidence_refs()      # cited EvidenceRef rows with tiers
  → for each ScenarioTemplate:
        match required_signals
        compute supporting / missing
        compute_confidence()
        build HypothesisEvaluation
  → sort by confidence descending
  → primary = rank[0]
  → alternatives = rank[1..4] (+ insufficient-data fallback if <2)
  → inject alternative_explanations cross-links
  → HypothesisEngineResult
```

### 3.2 Signal derivation (examples)

| Signal | Derivation |
|--------|------------|
| `proxy_enabled` | `registry.proxy_enable == 1` |
| `localhost_proxy` | ProxyServer contains 127.0.0.1 / localhost |
| `listener_absent` | `process.listener_found == False` |
| `listener_present` | `process.listener_found == True` |
| `browser_https_fail` | `network.browser_https_ok == False` or timeline event |
| `direct_path_ok` | `network.direct_path_ok == True` |
| `proof_path_contrast` | direct OK + browser fail |
| `registry_writer_telemetry` | writer_confirmed + telemetry sources |
| `wininet_winhttp_mismatch` | WinHTTP direct + proxy enabled |

### 3.3 Scenario library

| hypothesis_id | incident_type | base_rank |
|---------------|---------------|-----------|
| hyp-dead-wininet-proxy | DEAD_PROXY_CONFIG | high |
| hyp-unknown-local-listener | UNKNOWN_LOCAL_PROXY | low |
| hyp-dns-ok-browser-fail | DNS_OK_BROWSER_FAIL | medium |
| hyp-tls-mitm-indicators | POSSIBLE_MITM_RISK | medium |
| hyp-vpn-route-conflict | VPN_ROUTE_CONFLICT | low |
| hyp-benign-dev-proxy | KNOWN_DEV_PROXY | medium |
| hyp-insufficient-data | ERROR_INSUFFICIENT_DATA | low |

Scenarios with **zero required signal matches** are excluded (except insufficient-data fallback).

---

## 4. Confidence calculation model

**Not a probability.** Ordinal heuristic capped at **0.98**.

```text
score = base_rank
      + tier_bonus          # max tier among supporting evidence (0–0.12)
      + 0.06 × coverage     # required_signals matched / total
      + 0.05 × proof_hits   # proof_signals matched
      + 0.04 × cross_domain # registry AND (network OR process)
      − 0.06 × missing_count

score = clamp(score, 0.10, 0.98)
rank  = high if ≥0.80 | medium if ≥0.58 | else low
```

| base_rank | Base score |
|-----------|------------|
| low | 0.45 |
| medium | 0.72 |
| high | 0.88 |

| Evidence tier | Bonus |
|---------------|-------|
| OBSERVED_ONLY | 0.00 |
| CORRELATED | 0.04 |
| PROVEN_REGISTRY_WRITER | 0.08 |
| PROVEN_NETWORK_IMPACT | 0.10 |
| FINAL_CAUSATION | 0.12 |

**Explanation template:** base rank, coverage, proof hits, cross-domain, missing penalty, tier bonus, explicit “not calibrated probability.”

---

## 5. Example outputs

### 5.1 CS1 — Dead WinINET proxy (primary)

```json
{
  "hypothesis_id": "hyp-dead-wininet-proxy",
  "title": "Dead WinINET localhost proxy",
  "hypothesis": "Browser failure is likely caused by WinINET proxy pointing at a localhost port with no active listener.",
  "confidence": 0.91,
  "confidence_rank": "high",
  "confidence_display": "ordinal 0.91 (heuristic rank, not probability or certainty)",
  "confidence_explanation": "Base rank 'high' → 0.88. Required signal coverage 3/3. Cross-domain corroboration (registry + network/process). Penalty for 2 missing evidence item(s). Score is ordinal heuristic — not calibrated probability.",
  "supporting_evidence": [
    {
      "evidence_id": "ev-registry",
      "kind": "registry",
      "signal": "proxy_enable",
      "tier": "OBSERVED_ONLY",
      "observed_value": "1",
      "summary": "ProxyEnable=1, ProxyServer=127.0.0.1:59081",
      "is_proof": false
    },
    {
      "evidence_id": "ev-process",
      "kind": "process",
      "signal": "listener_found",
      "tier": "OBSERVED_ONLY",
      "observed_value": "False",
      "summary": "Listener on port 59081: False",
      "is_proof": false
    }
  ],
  "missing_evidence": [
    "Missing evidence for stronger claim: proof_path_contrast",
    "Missing evidence for stronger claim: registry_writer_telemetry"
  ],
  "alternative_explanations": [
    "Application-path failure with healthy DNS",
    "Insufficient evidence for strong hypothesis"
  ],
  "recommended_actions": [
    "Run structured proof (diagnose --proof)",
    "Preview DISABLE_WININET_PROXY with typed confirmation",
    "Monitor with proxy-watch for reverter respawn"
  ],
  "limitations": [
    "Does not prove malware or MITM.",
    "Registry observation does not identify who wrote ProxyEnable."
  ],
  "incident_type": "DEAD_PROXY_CONFIG"
}
```

### 5.2 Unknown listener (competing hypothesis)

```json
{
  "hypothesis_id": "hyp-unknown-local-listener",
  "title": "Unknown localhost proxy listener",
  "confidence": 0.49,
  "confidence_rank": "low",
  "missing_evidence": [
    "Missing evidence for stronger claim: registry_writer_telemetry",
    "Missing evidence for stronger claim: process_signature_verification"
  ],
  "recommended_actions": [
    "Collect Sysmon E13 or Procmon registry writer evidence",
    "Human review — do not auto-kill process"
  ]
}
```

---

## 6. Test cases

| Test | Asserts |
|------|---------|
| `test_cs1_dead_proxy_primary_hypothesis` | DEAD_PROXY_CONFIG, confidence ≤ 0.98, missing writer telemetry |
| `test_always_provides_competing_hypotheses` | ≥2 distinct hypothesis titles |
| `test_observation_separated_from_proof` | OBSERVED_ONLY refs have `is_proof=False` |
| `test_unknown_listener_competing_hypothesis` | UNKNOWN_LOCAL_PROXY in primary or alternatives |
| `test_never_claims_certainty_in_limitations` | No "proven malware", "guaranteed" |
| `test_confidence_explanation_present` | Non-empty explanation with heuristic language |
| `test_recommended_actions_are_preview_not_execute` | No auto-kill / execute |
| `test_insufficient_data_fallback` | Empty input → ERROR_INSUFFICIENT_DATA |

Run:

```powershell
pytest -q tests/test_hypothesis_engine_multievidence.py
```

---

## 7. Integration points

| Consumer | Usage |
|----------|-------|
| Investigation orchestrator | `evaluate_hypotheses()` after proof envelope |
| RAG retrieval | Index `hypothesis_id` + `incident_type` as metadata |
| Policy engine | `recommended_actions` → preview only |
| CLI (planned) | `python -m windows_network_toolkit investigate --hypotheses` |
| API | `POST /v1/investigations/{id}/hypotheses` |

---

## 8. Related docs

- [proof-vs-observation.md](proof-vs-observation.md)
- [case-study-1-proxy-drift.md](case-study-1-proxy-drift.md)
- [ai_investigation_platform_architecture.md](ai_investigation_platform_architecture.md)
- `src/platform_core/principles/` — epistemic gates

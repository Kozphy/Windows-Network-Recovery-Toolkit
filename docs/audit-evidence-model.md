# Audit Evidence Model

**Status:** Normative evidence tier and normalization reference  
**Modules:** `windows_network_toolkit/evidence_schema.py`, `src/platform_core/governance/proof_tier.py`, `proxy_state_machine.py`  
**Disclaimer:** Evidence tiers label **claim strength** — they do not auto-upgrade proof when exported to Power BI or governance reports.

---

## Purpose

The audit evidence model defines how raw CLI and watch observations become **normalized**, **tier-labeled**, **limitation-bearing** records suitable for classification, control testing, audit hash chains, and analytics export.

Design goals:

1. Preserve `raw_snapshot` for deterministic replay
2. Never collapse observation into proof in downstream dashboards
3. Align endpoint tiers (T0–T5) with governance proof tiers (T0–T4) via explicit mapping
4. Append standard limitations on every normalized event

---

## Evidence tiers T0–T5 (endpoint analytics)

Defined in `EvidenceTier` enum (`evidence_schema.py`). Aligned with [proxy-proof-ladder.md](proxy-proof-ladder.md).

| Tier | Enum value | Claim strength | Typical source |
|------|------------|----------------|----------------|
| **T0** | `T0_OBSERVATION` | Raw observation, no structural proof | Log line, uncorroborated note |
| **T1** | `T1_STATE_EVIDENCE` | Configuration state read | `proxy-status`, `proxy_change` normalizer |
| **T2** | `T2_RUNTIME_EVIDENCE` | Runtime listener/process correlation | `proxy-owner`, listener on port |
| **T3** | `T3_PATH_EVIDENCE` | Path contrast / probe results | `proxy-health`, direct vs proxy probes |
| **T4** | `T4_WRITER_PROOF` | Registry writer telemetry | Sysmon E13, Procmon, Security 4657 |
| **T5** | `T5_GOVERNANCE_PROOF` | Human-confirmed action in audit | Typed confirmation + apply logged |

### Tier upgrade rules

- Tiers are **assigned at normalization** — downstream scoring or charts must not silently promote T1 → T3.
- Listener with `sysmon_event_id == 13` or `writer_proof` flag → listener normalizer may emit T4.
- T5 requires explicit audit record of operator-confirmed apply — not inferred from successful probe.

### Standard limitations (always applicable)

From `STANDARD_LIMITATIONS`:

1. Listener ownership is correlation, not registry writer proof.
2. Registry writer attribution requires Sysmon, Procmon, ETW, or EventLog evidence.
3. Successful proxy probe does not prove the proxy is safe or intended.
4. Risk classification is a triage signal, not a malware verdict.

---

## Governance proof tier mapping (Power BI / reports)

`powerbi_star_export.py` and `audit_report.py` use platform proof tiers:

| Platform tier | Endpoint analytics tier | Description |
|---------------|-------------------------|-------------|
| `T0_OBSERVATION_ONLY` | T0 | Snapshot or symptom — not proof |
| `T1_LOCAL_CONFIG_EVIDENCE` | T1 | Registry/proxy configuration |
| `T2_RUNTIME_CORROBORATION` | T2 | Listener/path contrast |
| `T3_BEHAVIORAL_REPRODUCTION` | T3 | Structured proof checks |
| `T4_OPERATOR_CONFIRMED` | T5 | Human-confirmed action in audit |

**Note:** Endpoint T4 (writer proof) maps to platform T2–T3 depending on export context — consumers must read `limitations[]`, not tier name alone.

---

## Evidence types

| `evidence_type` | Normalizer | Default tier | Key normalized fields |
|-----------------|------------|--------------|------------------------|
| `proxy_state` | `normalize_proxy_state` | T1 | `wininet_proxy_enabled`, `wininet_proxy_server`, `wininet_winhttp_mismatch` |
| `listener_state` | `normalize_listener_state` | T2 (T4 if writer proof) | `listener_found`, `listener_pid`, `listener_name`, `listener_path` |
| `probe_result` | `normalize_probe_result` | T3 | `direct_probe_ok`, `proxy_probe_ok`, `proxy_status`, `failure_reason` |
| `proxy_change` | `normalize_proxy_change_event` | T1 | `old_proxy_server`, `new_proxy_server`, `reverter_suspected` |

Transition events from `proxy_state_machine.build_proxy_evidence_event` add:

- `before_state` / `after_state`
- `transition_class`, `proof_tier` (T0–T3 internal)
- `attribution`, `classification` bundle

---

## Normalization pipeline

```text
Raw CLI JSON / audit row / watch event
    → source-specific normalizer (evidence_schema)
    → EvidenceEvent { event_id, tier, limitations, raw_snapshot }
    → analytics_pipeline._dedupe_events
    → incident_classifier → IncidentRecord
    → control_tests.run_endpoint_control_tests
    → risk_scoring_engine
    → audit append (hash chain)
    → powerbi_star_export / governance-report
```

### Deterministic identity

- `make_event_id(timestamp_utc, evidence_type, stable_fields)` — sorted JSON hash, 24 hex chars.
- Transition ids: `make_transition_event_id(timestamp, before, after)`.
- Incident ids: `make_incident_id(timestamp, class, endpoint)`.

### Deduplication

Duplicate `event_id` within a pipeline run are dropped — replays must use fresh timestamps or different stable fields to create distinct rows.

### Coalescing (proxy-watch)

`coalesce_proxy_events` merges observations within configurable window (default 1000 ms) into single transition — preserves `raw_sub_events` for audit.

---

## Evidence quality dimensions

| Dimension | Question | Failure if ignored |
|-----------|----------|-------------------|
| **Completeness** | Are state, listener, and probe events present? | NOT_TESTED controls, `ERROR_INSUFFICIENT_DATA` |
| **Freshness** | Timestamps within incident window? | Stale classification |
| **Tier honesty** | Is tier label consistent with sources? | Audit finding overturned in interview |
| **Limitation visibility** | Are caveats exported to BI? | Dashboard implies malware |
| **Chain integrity** | Does audit verify pass? | Governance report unreliable for legal hold |

---

## Limitations (honest bounds)

### What the evidence model supports

- Repeatable normalization from fixtures and live Windows endpoints
- Tier-labeled export for PL-300 and Big 4 workshop narratives
- Replay from `raw_snapshot` without re-running live probes (fixture mode)

### What it does not support

- **Population inference** — one endpoint bundle ≠ fleet prevalence
- **Writer proof by default** — requires optional telemetry integration
- **MITM confirmation** — path probes support triage only
- **Non-repudiation of operators** — hash chain proves log order, not biometric identity
- **Cross-platform registry** — WinINET-focused; Linux CI uses fixtures

### Recovery procedures

| Gap | Recovery action |
|-----|-----------------|
| Missing probes | Re-run `proxy-health` with network access |
| Missing owner | Re-run `proxy-owner` elevated |
| Missing writer proof | Enable Sysmon E13; collect Procmon registry trace |
| Chain break | Restore from backup; investigate tamper; do not attest period |

---

## Audit language examples

**Allowed:** "Evidence tier T3 path contrast supports dead localhost proxy hypothesis; writer proof unavailable (T4 not met)."

**Prohibited:** "T3 proves attacker modified registry."

**Allowed:** "Normalized `probe_result` shows direct_probe_ok=true, proxy_probe_ok=false."

**Prohibited:** "Probe proves endpoint compromised."

---

## Related documents

- [proxy-proof-ladder.md](proxy-proof-ladder.md) — worked examples per tier
- [domain-model.md](domain-model.md) — entity definitions
- [audit-hash-chain-explained.md](audit-hash-chain-explained.md) — integrity vs truth
- [proof-vs-observation.md](proof-vs-observation.md) — proof envelope vs tiers

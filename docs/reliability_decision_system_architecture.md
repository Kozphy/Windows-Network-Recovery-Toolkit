# Reliability decision system architecture

**Audience:** reliability engineering, security engineering, Big 4 IT assurance / SOC 2 style control design.  
**Scope:** how the Endpoint Reliability Platform (Windows Network Recovery Toolkit) evolves from a diagnostic toolkit into an **evidence-aware** local-first decision system—without breaking beginner `.bat` flows or existing `python -m src` contracts.

**Normative vocabulary:** pipeline stages and evidence tiers are defined in code in `platform_core/decision_pipeline_contract.py` (`ORDERED_PIPELINE_STAGES`, `EvidenceTier`, `resolve_evidence_tier`).

---

## 1. Decision pipeline (end-to-end)

| Stage | Meaning | Primary implementation today | Audit hook (target) |
| --- | --- | --- | --- |
| **OBSERVE** | Raw probes, registry reads, env/git/npm reads | `src/` collectors, `failure_system/`, `endpoint_agent/`, `agent/collector.py`, live snapshot paths | `observation` / `snapshot_ingest` rows |
| **CLASSIFY** | Layer / failure bucket / signal normalization | Layer decision v2, `platform_core/failure_scenarios.py`, policy hints | `classification` rows |
| **HYPOTHESIZE** | Ranked hypotheses, confidence (ordinal) | `platform_core/reasoning_engine.py`, live scorer | `hypothesis_rank` rows |
| **VERIFY** | Contrast / proof checks (read-only) | Proof engine (`diagnose --proof`, `diagnose-live --proofs`), `ProofResult` | `proof_run` rows |
| **POLICY_CHECK** | ALLOW / PREVIEW / BLOCK from evidence + risk + trust | `platform_core/reasoning_engine.py` (`evaluate_reasoning_policy`), `platform_core/policy.py`, `platform_core/policy_engine.py`, route gates | `policy_decision` rows |
| **PREVIEW** | Dry-run default, structured intended mutations | `POST /platform/remediation/preview`, CLI `preview`, proxy disable preview | `remediation_preview` |
| **CONFIRM** | Typed confirmation phrases, allowlist | `src/command_handlers_safety.py`, platform execute models | `confirmation_received` / `confirmation_rejected` |
| **EXECUTE** | Allowlisted subprocess / registry writers only | `backend/platform_routes.py`, `backend/live_observability.py` (fixed argv to `python -m src …`) | `remediation_execute` |
| **VALIDATE** | Post-change read-only probes | `src/proxy_guard/connectivity.py`, guard decision path | `post_change_validation` |
| **AUDIT** | Append-only JSONL, replayable | `logs/*.jsonl`, `platform_data/audit.jsonl`, `platform_core/reasoning_audit.py` | every row includes `schema_version`, `timestamp`, `correlation_id` where applicable |

**Note:** stages are **logical**; one HTTP request may span PREVIEW only, or CONFIRM+EXECUTE+VALIDATE+AUDIT in one transaction on the server side. The assurance requirement is that **no stage is skipped silently** for mutations.

---

## 2. Evidence tiers (assurance ladder)

| Tier | ID | Meaning | Maps from (legacy / existing) |
| --- | --- | --- | --- |
| 0 | `TIER_0_RAW_OBSERVATION` | Single-source facts (ping, reg value, curl exit) | `Observation.evidence_level == "observed"` |
| 1 | `TIER_1_CORRELATED_SIGNAL` | Multi-signal inference, events, transitions | `EvidenceLevel` in `inferred`, `validated`; `EndpointEvent` detection |
| 2 | `TIER_2_CONTRAST_TESTED` | Proof checks ran; outcome not causal confirmation | `ProofResult` with `checks_run` and status `REJECTED` / `INCONCLUSIVE` / non-`NOT_RUN` |
| 3 | `TIER_3_CAUSAL_PROOF` | Scoped causal contrast succeeded | `ProofResult.status == "CONFIRMED"` (narrow hypothesis scope—documented in proof payloads) |

**Registry writer (Sysmon / Security log):** treat as **Tier 1–2 attribution evidence** depending on configuration—**not** Tier 3 causal proof of user intent. Product language: *attribution evidence, not absolute proof* (`evidence/registry_writer_proof.py`, `docs/evidence_pipeline.md`).

**Resolver:** `resolve_evidence_tier(proof=..., observation_evidence_ceiling=...)` in `decision_pipeline_contract.py` gives a single **dominant** tier per slice for policy UX and audit tags.

---

## 3. Last Known Good (LKG) snapshot

**Goal:** store and compare known-good **network / proxy / DNS / WinHTTP / browser-path** posture for rollback and drift narratives.

**Existing surfaces:**

- `logs/proxy_known_good_snapshots.jsonl`, `config/last_known_good_proxy.json` — CLI proxy known-good path (`src/proxy_guard/proxy_snapshot_commands.py`, `src/cli.py`).
- `proxy restore-lkg` — typed confirmation restore (`src/command_handlers_safety.py`).
- Platform LKG metadata routes under `backend/platform_routes.py` (`/platform/lkg/*`).

**Target state (migration):**

- One **canonical LKG record schema** (Pydantic) shared by CLI and `/platform/lkg/snapshot` with fields: WinINET tuple, WinHTTP proxy text, optional DNS summary, optional Git/npm/env/browser-policy snapshot IDs (references only—no secrets).
- Diff engine compares **current observation bundle** vs latest LKG for dashboards (`diff_snapshots` pattern already in `proxy_guard`).

---

## 4. Confirmation gate

**Control objective:** no registry / network-changing action without **explicit** operator confirmation (typed phrase + allowlisted action key).

**Existing:** remediation registry, `dry_run=True` default on execute APIs, `command_handlers_safety.py`, proxy disable / restore-LKG phrases, `agent/executor.py` confirmed-script allowlist.

**Target:** every mutation executor records `pipeline_stage=CONFIRM` outcome before `EXECUTE` in the same correlation ID.

---

## 5. Post-change validation

**Control objective:** every successful mutation runs read-only validation and logs **before / after** summaries.

**Existing:** `src/proxy_guard/connectivity.py`, audit hooks in guard paths, repair audit JSONL.

**Target:** unify a `ValidationBundle` model (timestamps, probe names, exit codes redacted where needed) referenced from `remediation_execute` audit rows.

---

## 6. Proxy writer attribution (optional telemetry)

**Objective:** optional Sysmon / Event ID 4657–style evidence for **who likely touched** WinINET-relevant keys.

**Existing:** `evidence/registry_writer.py`, `evidence/registry_writer_proof.py` (strict JSON contract).

**Assurance:** label as **attribution**; never upgrade to Tier 3 causal proof based on telemetry alone; keep `limitations[]` populated when telemetry is missing or ambiguous.

---

## 7. Policy engine integration

**Outcomes:** `ALLOW` | `PREVIEW` | `BLOCK` (already in `reasoning_models.PolicyOutcome`).

**Inputs:** evidence tier (via `resolve_evidence_tier`), risk / impact (`ReliabilityImpact`), confidence (ordinal), trust (conflicts, proof), explicit confirmation.

**Authoritative evaluators today:** `platform_core/reasoning_engine.py`, `platform_core/policy.py`, route-level RBAC + allowlists.

**Non-authoritative hint:** `policy_outcome_hint` in `decision_pipeline_contract.py` for tests and dashboard copy—**must not** bypass router gates.

---

## 8. Audit model (JSONL)

**Append-only** streams (examples—exact filenames depend on deployment):

- `platform_data/audit.jsonl` — platform prototype actions.
- `logs/repair_audit.jsonl`, `logs/safety_audit.jsonl`, `logs/proxy_hijack_audit.jsonl`, `logs/decision_runs.jsonl`, `logs/lkg_snapshots.jsonl` (as wired).

**Recommended envelope fields (migration target):**

- `schema_version`, `event_type`, `pipeline_stage`, `evidence_tier`, `correlation_id`, `endpoint_id` (if fleet), `policy_outcome`, `reason_codes[]`, `action_key`, `dry_run`, `confirmation_ok`, `before_summary`, `after_summary`, `validation_summary`, `limitations[]` (no secrets, no full proxy credentials in clear text).

---

## 9. Proposed folder / module map

| Area | Current | Proposed addition (incremental) |
| --- | --- | --- |
| Vocabulary | — | `platform_core/decision_pipeline_contract.py` (**done**) |
| Audit envelope | scattered JSONL writers | `platform_core/reliability_audit_event.py` (single `ReliabilityAuditEvent` model + redaction helpers) — **phase 2** |
| LKG | proxy_guard + platform routes | shared `platform_core/lkg_contract.py` — **phase 2** |
| Validation | `proxy_guard/connectivity.py` | `platform_core/post_change_validation.py` thin wrapper — **phase 2** |

No large directory rename required.

---

## 10. API / CLI changes (by phase)

**Phase 0 (no breaking changes):** add optional JSON fields `evidence_tier`, `pipeline_stage` on new audit rows only; keep existing CLI flags.

**Phase 1:** `python -m src diagnose-live --json` includes `evidence_tier_resolved` from `resolve_evidence_tier` (additive field).

**Phase 2:** `/platform/remediation/execute` response echoes `evidence_tier` + `validation_bundle_id`.

**Phase 3:** frontend dashboard filters by tier and stage (read-only).

---

## 11. Tests (strategy)

| Layer | Tests |
| --- | --- |
| Contract | `tests/test_decision_pipeline_contract.py` (**done**) — tier resolution, pipeline order, hint semantics |
| Policy | `tests/test_policy_reasoning.py`, existing policy / remediation tests |
| Safety | `tests/test_proxy_restore_lkg_confirmation.py`, API confirmation tests |
| Audit | extend storage tests when `ReliabilityAuditEvent` lands |

---

## 12. Migration plan (assurance-friendly)

1. **Inventory:** list all JSONL writers and event `type` strings (grep `jsonl`, `append`).
2. **Vocabulary:** adopt `decision_pipeline_contract` in one writer (e.g. reasoning audit) as pilot.
3. **Dual-write:** old + new envelope fields for two releases (if shipping externally).
4. **Replay:** `python -m src replay` and platform replay routes must ignore unknown fields (forward compatible).
5. **Cutover:** remove deprecated fields only after dashboard/consumers updated.
6. **Control testing:** sample N audit rows per stage; verify no `EXECUTE` without preceding `CONFIRM` for registry actions.

---

## 13. What **not** to change

- **`scripts/*.bat`:** beginner flows, wording, and safety prompts stay stable unless a critical defect is found.
- **Default CLI behavior:** existing subcommands and defaults (especially dry-run / preview-first) must remain backward compatible.
- **No arbitrary shell from API:** `backend/live_observability.py` must keep fixed `python -m src` argv bridges only.
- **Blocked destructive paths:** silent firewall reset, silent adapter disable, silent process kill—remain **off** or manual-only.
- **Authoritative policy:** do not replace `reasoning_engine` / `policy.py` with `policy_outcome_hint` alone—the hint is for alignment and tests only.

---

## 14. Open gaps (honest backlog)

- Single unified `ReliabilityAuditEvent` schema across all JSONL sinks.
- Explicit `pipeline_stage` on every mutation path (some writers still event-type only).
- Tier 3 scope strings on proof payloads consumed consistently in UI copy.
- `agent/collector.py` WinINET vs WinHTTP ordering is legacy—document or refactor under OBSERVE without breaking callers.

---

## References

- `docs/event_state_reasoning_platform.md` — reasoning chain
- `docs/safety_model.md`, `docs/proxy_remediation_contract.md` — gates and LKG
- `docs/evidence_pipeline.md` — registry writer proof boundaries
- `platform_core/decision_pipeline_contract.py` — normative tier + stage constants

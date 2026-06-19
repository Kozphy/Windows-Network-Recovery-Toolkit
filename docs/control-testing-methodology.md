# Control Testing Methodology

**Status:** Operational methodology for endpoint proxy control tests  
**Modules:** `windows_network_toolkit/control_tests.py`, `src/platform_core/controls/control_test.py`, `src/platform_core/risk/control_test_mature.py`  
**Disclaimer:** Control tests evaluate **design effectiveness for scoped evidence** — not regulatory operating effectiveness over a full population.

---

## Purpose

Control testing answers: *Given the evidence collected for this endpoint incident, do our defined controls support or contradict the classified finding — and what should a human do next?*

The methodology is **read-only**, **evidence-backed**, and **explicitly limited**.

---

## Test execution flow

```text
1. Collect evidence
   proxy-status → proxy-health → proxy-owner → proxy-watch (optional)

2. Normalize to EvidenceEvent[] (evidence_schema)

3. Classify incident (incident_classifier)

4. Run control tests
   run_endpoint_control_tests()           # six endpoint controls
   OR map_control_tests_from_incident()   # incident-refined
   OR run_mature_control_tests(fixture)   # CTRL-EPR-001…006 for governance
   OR run_control_test_suite(audit_records)  # platform audit suite

5. Aggregate for risk scoring (worst-case control outcome)

6. Export to governance-report / powerbi-export
```

### CLI entry points

```powershell
# Fixture-based control test
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json

# Full analytics pipeline (includes controls)
python -m windows_network_toolkit analytics-summary --audit-dir tests/fixtures/risk_analytics/audit_sample

# Governance report with control summary
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

---

## Outcome semantics

| Outcome | Meaning | Audit language |
|---------|---------|----------------|
| **PASS** | Control objective met for scoped evidence | "Control operated as designed for this incident scope." |
| **FAIL** | Control objective not met — action or review needed | "Control gap identified — see evidence and recommendation." |
| **PARTIAL** | Some evidence present; proof incomplete | "Additional evidence required — see limitations." |
| **NOT_TESTED** | Preconditions absent or out of scope | "Control not applicable or not exercised for this scenario." |

### Platform mapping notes

`governance-report` maps platform suite outcomes:

- `INSUFFICIENT_EVIDENCE` → counted as NOT_TESTED
- `EXCEPTION` → counted as PARTIAL

---

## Endpoint control catalog (six tests)

From `run_endpoint_control_tests()` — stable order:

| Order | control_id | CTRL framework |
|-------|------------|----------------|
| 1 | `WININET_LOCALHOST_PROXY_HEALTH` | CTRL-001, CTRL-003 |
| 2 | `WININET_PROXY_OWNER_VERIFICATION` | CTRL-004 |
| 3 | `PROXY_REVERTER_DETECTION` | CTRL-007 |
| 4 | `DIRECT_VS_PROXY_PATH_COMPARISON` | CTRL-008 |
| 5 | `SAFE_REMEDIATION_POLICY` | CTRL-009 |
| 6 | `WININET_WINHTTP_ALIGNMENT` | CTRL-002 |

### Inputs per test

| Test | Required inputs |
|------|-----------------|
| Localhost health | `proxy_state`, `health_audit` |
| Owner verification | `proxy_state`, `owner`, optional `health_audit` |
| Reverter | `reverter_diagnosis` |
| Direct vs proxy | `health_audit` |
| Safe remediation | None (toolkit defaults assertion) |
| WinINET/WinHTTP | `proxy_state` |

---

## Incident-refined testing

`map_control_tests_from_incident()` refines outcomes based on `incident.incident_class`:

| Incident class | Refinement behavior |
|--------------|---------------------|
| `DEAD_PROXY_CONFIG` | Forces FAIL on localhost health |
| `LOCAL_PROXY_ACTIVE`, `UNKNOWN_LOCAL_PROXY` | Owner PASS only if T4 writer proof in events |
| `DIRECT_ONLY_WORKS`, `BOTH_DIRECT_AND_PROXY_FAIL` | Path comparison FAIL |
| `REVERTER_SUSPECTED`, `PROXY_FLAPPING` | Reverter FAIL + human interpretation in evidence |
| `WININET_WINHTTP_MISMATCH` | Alignment FAIL |

**Audit note:** Refinement adjusts labels for explainability — auditors should review raw `health_audit` and `raw_snapshot` separately.

---

## Mature control tests (governance fixtures)

`run_mature_control_tests(fixture)` produces `ControlTestMatureRecord` for CTRL-EPR-001 … CTRL-EPR-006 — classification-scoped catalog used in portfolio case studies and Power BI seed data.

Each record includes:

- `control_id`, `control_name`, `control_objective`
- `test_procedure`, `evidence_required[]`
- `test_result`, `residual_risk`, `limitation`
- `remediation_owner`, `review_frequency`

---

## Evidence used by outcome

### PASS examples

- **Localhost health PASS:** `proxy_status=HEALTHY_LOCALHOST_PROXY` with probe evidence
- **Safe remediation PASS:** Documented read-only defaults, dry-run disable, no auto kill
- **Reverter PASS:** No flapping pattern in timeline window
- **Alignment PASS:** WinINET disabled or stacks aligned

### FAIL examples

- **Localhost health FAIL:** `DEAD_LOCALHOST_PROXY` — direct works, proxy fails
- **Owner FAIL:** Proxy enabled, no listener found
- **Reverter FAIL:** `REVERTER_SUSPECTED` status with timeline evidence
- **Path FAIL:** `direct_probe_ok=true`, `proxy_probe_ok=false`

### PARTIAL examples

- **Owner PARTIAL:** Listener found, process name known, no Sysmon E13
- **Health PARTIAL:** Ambiguous proxy_status; re-run health recommended
- **Reverter PARTIAL:** Suggestive pattern, incomplete window

### NOT_TESTED examples

- Proxy disabled → localhost health and owner NOT_TESTED
- No health audit → path comparison NOT_TESTED
- Incident class out of scope for mature CTRL-EPR-00x → NOT_TESTED

---

## Reviewer notes (for internal audit / Big 4)

### Before accepting PASS

1. Confirm evidence tier meets control procedure minimum (usually T1+ for config, T3 for path).
2. Read `limitations[]` on each test — PASS with writer limitation is not attribution PASS.
3. Verify `SAFE_REMEDIATION_POLICY` PASS documents defaults — spot-check CLI `--dry-run` behavior.
4. For governance exports, distinguish endpoint six-pack vs mature CTRL-EPR catalog.

### Before escalating FAIL

1. FAIL does **not** authorize process kill or silent registry mutation.
2. Check `recommendation` field — typically preview-only with typed confirmation.
3. Confirm FAIL is not artifact of stale fixture or missing probe in CI.

### PARTIAL handling

Treat PARTIAL as **open item** — assign owner to collect T4 writer proof or complete health audit. Do not convert PARTIAL to FAIL or PASS in management reporting without evidence update.

### Population testing

This methodology is **per-incident**. Fleet-wide operating effectiveness requires:

- Sample size design (not included in toolkit)
- Independent reperformance of `proxy-health` on sample endpoints
- Separate ITGC reliance on hash chain (CTRL-010)

---

## Integration with risk scoring

`risk_scoring_engine` aggregates control outcomes:

| Aggregate | Score impact |
|-----------|--------------|
| FAIL | Increases score; triggers `human_review_recommended` |
| PARTIAL | Moderate increase |
| PASS | Neutral or slight decrease |
| NOT_TESTED | Treated as unknown — does not imply PASS |

---

## CI vs live Windows

| Environment | Behavior |
|-------------|----------|
| Linux CI | Golden fixtures drive PASS/FAIL/PARTIAL deterministically |
| Windows live | Registry reads, netstat, HTTPS probes — network dependent |
| Air-gapped | Fixture mode only; mark path controls PARTIAL or NOT_TESTED |

Tests: `tests/windows_network_toolkit/test_control_tests.py`, `tests/test_risk_decision_platform.py`

---

## Related documents

- [risk-control-framework.md](risk-control-framework.md) — CTRL-001 … CTRL-010 definitions
- [control-matrix.md](control-matrix.md) — Summary table
- [anti-code-paste-defense.md](anti-code-paste-defense.md) — Interview defense

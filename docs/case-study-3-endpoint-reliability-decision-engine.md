# Case Study 3: Endpoint Reliability Decision Engine

## Executive Summary

Multiple noisy signals — proxy drift, browser failures, DNS success, optional TLS anomalies — must be merged into a **single auditable decision** without collapsing observation into proof. The endpoint reliability decision engine normalizes signals, ranks hypotheses, applies policy gates, previews remediation, and writes append-only audit records. It supports safer operations for IT support, SRE, and risk consultants who need **replayable incident reasoning**, not one-off scripts.

## Situation

An operations team needed a consistent workflow for endpoint network incidents: diagnose → classify → prove (where possible) → policy → preview → audit → replay. Ad-hoc PowerShell fixes produced untracked registry changes and inconsistent root-cause narratives across shifts.

## Symptoms

- Inconsistent remediation playbooks across technicians
- No shared evidence format between L1 support and security review
- High-confidence guesses treated as confirmed root cause
- Remediation executed before rollback snapshots existed
- Post-incident reviews could not replay decision logic

## Initial Observation

The platform ingests normalized signal maps, for example from proxy drift replay:

```jsonl
{"timestamp": "2026-06-09T10:01:00Z", "signal": "PROXY_ENABLE", "observed_value": "ProxyEnable=1"}
{"timestamp": "2026-06-09T10:01:15Z", "signal": "wininet_winhttp_divergent", "observed_value": "true"}
{"timestamp": "2026-06-09T10:02:00Z", "signal": "browser_https_failed", "observed_value": "true"}
{"timestamp": "2026-06-09T10:02:10Z", "signal": "direct_path_success", "observed_value": "true"}
```

These are **observations** until the proof engine validates structured contrast checks.

## Hypothesis

| # | Hypothesis | Engine mapping |
|---|------------|----------------|
| H1 | WinINET proxy drift with working direct path | `WININET_PROXY_DRIFT` / `PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS` |
| H2 | Unknown localhost listener | `UNKNOWN_LOCAL_PROXY` |
| H3 | Registry reverter respawn | `REVERTER_SUSPECTED` (via `proxy-watch`) |
| H4 | MITM / TLS interception | `POSSIBLE_MITM_RISK` (requires TLS proof indicators) |

## Evidence Collected

### Pipeline architecture

```text
Collectors → Evidence fusion → Hypothesis ranking → Policy engine → Remediation preview → Audit JSONL → Replay
```

**Canonical modules:** `src/platform_core/` (evidence, proof, policy, audit)  
**CLI facade:** `windows_network_toolkit/`  
**Decision ranking:** `windows_network_toolkit/decision/hypothesis_engine.py`

### Commands — full decision path (fixture-safe)

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

# 1) Observe + classify
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json

# 2) Structured proof
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json

# 3) Merged evidence report (Observation → Hypothesis → Proof)
python -m windows_network_toolkit evidence-report --url https://example.com `
  --fixture tests/fixtures/enert/registry_writer_observed.json --format markdown

# 4) Policy-gated remediation preview
python -m windows_network_toolkit proxy-disable --dry-run

# 5) Replay incident timeline
python -m toolkit replay windows_network_toolkit/examples/proxy_drift_incident.jsonl
python -m toolkit report windows_network_toolkit/examples/proxy_drift_incident.jsonl --format markdown

# 6) Verify audit chain
python -m windows_network_toolkit audit verify logs/canonical_decision_audit.jsonl
```

### API path (optional demo)

```powershell
uvicorn backend.main:app --reload
# POST /platform/diagnose
# POST /platform/remediation/preview  (dry_run=true default)
# GET  /platform/evidence/timeline
```

### Evidence tiers

| Level | Claim strength |
|-------|----------------|
| `OBSERVED_ONLY` | Registry/netstat reads |
| `CORRELATED` | Listener/process match |
| `PROVEN_REGISTRY_WRITER` | Sysmon E13 / Procmon |
| `PROVEN_NETWORK_IMPACT` | Path impact + writer proof |
| `FINAL_CAUSATION` | Writer + port owner or network impact |

### Policy outcomes (representative)

| Condition | Policy decision |
|-----------|-----------------|
| High confidence, unproven | `PREVIEW_ONLY` |
| Proof confirmed, safe tier action | `ALLOW` (with confirmation) |
| Proof rejected | `BLOCK` |
| Low confidence | `BLOCK` |
| Destructive action requested | `BLOCK` (kill, firewall, adapter) |

### Test contracts enforcing safety

```powershell
pytest -q tests/test_policy_safety_contract.py
pytest -q tests/test_evidence_level_contract.py
pytest -q tests/test_replay_determinism.py
pytest -q tests/test_portfolio_case_studies.py
```

## Analysis

The decision engine **supports** ranking `WININET_PROXY_DRIFT` when:

- `browser_https_failed` and `direct_path_success` co-occur
- WinINET/WinHTTP divergence is observed
- Proof envelope returns `supported` for path contrast

It **weakens** automatic remediation when:

- Evidence tier is below proof threshold
- Confidence is ordinal but causation is unproven
- Classification is `UNKNOWN_LOCAL_PROXY` with low attribution score

Deterministic replay (`engine_digest` SHA-256) ensures the same inputs produce the same decision narrative — critical for SRE postmortems and audit.

## Decision

**Platform recommendation:** Execute the canonical pipeline before any host mutation:

1. Collect evidence (read-only)
2. Rank hypotheses
3. Attempt proof where applicable
4. Evaluate policy
5. Preview remediation
6. Require typed confirmation
7. Append audit record
8. Enable replay for post-incident review

For the golden dead-proxy fixture, recommended action: `DISABLE_WININET_PROXY_WITH_CONFIRMATION`.

For unknown listener fixture, recommended action: `INVESTIGATE_LISTENER` (human review required).

## Action Taken

1. Deployed toolkit as standard L2 triage workflow (CLI + optional API)
2. Replaced ad-hoc registry scripts with dry-run-default commands
3. Enabled `.audit/*.jsonl` for all status reads and remediation previews
4. Integrated CI safety contract tests to prevent regression of destructive defaults
5. Used fixture replay for training and interview demos (cross-platform)

## Result

- Mean time to **consistent diagnosis** reduced (shared evidence format)
- Unsafe manual fixes reduced (policy blocks + confirmation tokens)
- Post-incident replay available for shift handoffs
- Risk and security stakeholders receive reports with explicit `limitations[]`
- Platform engineering narrative: deterministic, testable decision infrastructure

## Risk Controls

| Risk | Mitigation |
|------|------------|
| Wrong remediation | Dry-run default; typed confirmation; LKG snapshot |
| False certainty | Evidence tier guards; limitations in every output |
| Audit tampering | Append-only JSONL; hash-chain verification path |
| Autonomous containment | Adapters and API persist recommendations only — execution gated elsewhere |
| Destructive regression | CI contract tests block merge on safety violations |

**Blocked actions (never silent):** `KILL_PROXY_PROCESS`, `FIREWALL_RESET`, `ADAPTER_DISABLE`, `WINHTTP_MODIFY`

## Lessons Learned

| Principle | Application |
|-----------|-------------|
| **Observation ≠ Proof** | Signal JSONL is input; proof engine must validate before tier upgrade. |
| **Correlation ≠ Causation** | Hypothesis ranking uses correlation; policy gates require proof for strong actions. |
| **Confidence ≠ Certainty** | Ordinal scores drive policy rows — not Bayesian malware verdicts. |
| **Policy Permission ≠ Safety Guarantee** | `ALLOW` still requires confirmation, rollback, and audit for registry mutations. |

## Interview Talking Points

- Built **decision infrastructure**, not a chatbot — deterministic pipeline with test contracts
- Separated **Windows probes** from **canonical core** for maintainability and replay
- Implemented **evidence tier state machine** with upgrade guards
- Designed for **SRE workflows**: metrics, replay, append-only audit, fleet simulation hooks
- Explained **epistemic humility** as a product feature — limitations[] in API and CLI output
- CI enforces **zero skipped tests on Windows** and safety contracts on every PR
- Suitable for **platform engineering** and **IT risk** portfolios — observability + governance

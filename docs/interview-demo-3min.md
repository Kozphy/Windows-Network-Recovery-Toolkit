# 3-Minute Interview Demo

Timed script for FAANG / Big 4 / mixed panels. All commands use fixtures — safe on any OS.

**Canonical fixtures:** `fixtures/dead_proxy_config/`, `fixtures/wininet_winhttp_mismatch/`, etc.

---

## Unified Timeline (3:00)

### 0:00–0:20 — Problem

**Say:** “Browser fails while ping and DNS work. This is endpoint reliability—not ‘network down.’ We treat it as technology risk evidence, not a repair ticket.”

```powershell
python -m windows_network_toolkit proxy-status --fixture fixtures/dead_proxy_config/raw_signals.json
```

### 0:20–0:50 — Evidence

**Say:** “WinINET proxy enabled, WinHTTP direct, dead localhost port—structured signals, not screenshots.”

```powershell
python -m windows_network_toolkit diagnose --proof --fixture fixtures/dead_proxy_config/raw_signals.json
```

### 0:50–1:30 — Classification + proof tier

**Say:** “Classification: `DEAD_PROXY_CONFIG`. Proof tier T2—multiple independent signals. Observation is not proof.”

```powershell
type fixtures\dead_proxy_config\expected_classification.json
```

### 1:30–2:10 — Policy gate

**Say:** “Policy gate: preview-only. No silent registry change. Humans authorize apply.”

```powershell
python -m windows_network_toolkit proxy-disable --dry-run --fixture fixtures/dead_proxy_config/raw_signals.json
type fixtures\dead_proxy_config\expected_policy.json
```

### 2:10–2:40 — Audit + governance report

**Say:** “Hash-chained JSONL, timeline, committee report with limitations.”

```powershell
python -m windows_network_toolkit audit verify tests/fixtures/risk_analytics/audit_sample_chained
python -m windows_network_toolkit governance-report --fixture fixtures/dead_proxy_config/raw_signals.json --format markdown
```

### 2:40–3:00 — Why it matters

**Say:** “Endpoint reliability becomes auditable technology risk evidence—management information for governance, not an EDR verdict.”

Show: [reports/sample_governance_report.md](../reports/sample_governance_report.md)

---

## Path A — FAANG / platform / SRE

See [faang-platform-review.md](faang-platform-review.md). Emphasize state machine, replay, safety contracts.

```powershell
pytest -q tests/test_proxy_state_transitions.py tests/test_proxy_classifier_safety_contract.py
python -m windows_network_toolkit replay-demo --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
```

---

## Path B — Big 4 / technology risk / audit

See [big4-interview-defense.md](big4-interview-defense.md). Emphasize controls, proof tiers, non-claims.

```powershell
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit export-powerbi --audit-dir tests/fixtures/risk_analytics/audit_sample --out-dir analytics/powerbi/sample_csv
```

---

## Path C — MSc / research reviewer

See [research-framing.md](research-framing.md), [evaluation.md](evaluation.md), [msc-application-summary.md](msc-application-summary.md).

```powershell
pytest -q tests/evaluation/test_scenario_matrix_15.py
python -m windows_network_toolkit classifier-benchmark --cases examples/evaluation/classifier_benchmark_sample.json
```

---

## Extended demos

- [replay-demo.md](replay-demo.md)
- [demo-faang-big4-review.md](demo-faang-big4-review.md)

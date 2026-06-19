# 3-Minute Interview Demo

Pick **one path** based on who is in the room. All commands use fixtures — safe on any OS.

---

## Path A — FAANG / platform / SRE (3 minutes)

**Opening (15s):** “Browser broken, ping works — often dead WinINET localhost proxy. This is decision infrastructure: read-only evidence, deterministic classifiers, policy-gated preview only.”

| Step | Command | Say |
|------|---------|-----|
| 1 | `python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json` | “Structured state, not registry dumps.” |
| 2 | `python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json` | “Path contrast — observation with limitations.” |
| 3 | `python -m windows_network_toolkit proxy-disable --dry-run --fixture tests/fixtures/enert/dead_proxy_59081.json` | “Default dry-run; no silent mutation.” |
| 4 | `pytest -q tests/test_proxy_state_transitions.py tests/test_proxy_classifier_safety_contract.py` | “CI safety contracts on classifiers.” |

**Close (15s):** “Observability + gated recovery — not EDR. Hash-chained audit and replay in the full demo.”

---

## Path B — Big 4 / technology risk / audit (3 minutes)

**Opening (15s):** “Evidence indicates endpoint reliability risk — not malware. I'll show control tests, proof tiers, and governance output with explicit non-claims.”

| Step | Command | Say |
|------|---------|-----|
| 1 | `python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json` | “PASS/FAIL with limitations — design effectiveness.” |
| 2 | `python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json` | “Ordinal risk — not probability.” |
| 3 | `python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown` | “Management information — not audit opinion.” |
| 4 | `python -m windows_network_toolkit powerbi-export --audit-dir tests/fixtures/risk_analytics/audit_sample --out-dir examples/powerbi/export` | “Star schema for risk committee KPIs.” |

**Close (15s):** “CTRL-001–010 map to code. Writer proof requires Sysmon — we don't overclaim.”

---

## Path C — Mixed panel (3 minutes)

**Minute 1 — Problem + safety:** Dead proxy case study → [one-page-case-study-dead-proxy.md](one-page-case-study-dead-proxy.md)

**Minute 2 — Engineering:** `proxy-replay` on `tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl`

**Minute 3 — Risk:** `governance-report` + mention Power BI export

```powershell
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

---

## Extended demos

- [demo-faang-big4-review.md](demo-faang-big4-review.md) — 5-minute paths
- [replay-demo.md](replay-demo.md) — deterministic replay walkthrough
- [big4-interview-defense.md](big4-interview-defense.md) — reviewer Q&A

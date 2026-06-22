# Evidence-Based Endpoint Reliability Governance: A Windows Proxy Drift Case Study

## Abstract

Windows endpoints frequently exhibit application-layer connectivity failures while lower-layer network tests remain green. This project implements a **deterministic evidence pipeline** that transforms WinINET/WinHTTP proxy configuration, localhost listener state, and path probes into **classified incidents**, **proof tiers**, **policy-gated remediation previews**, and **audit-backed governance reports**. The contribution is methodological: reproducible triage with explicit limitations—not autonomous repair or security verdicts.

## Problem Statement

Organizations treat proxy drift, dead localhost listeners, and WinINET/WinHTTP mismatch as ad-hoc IT tickets. Without structured evidence, operators conflate observation with proof, apply registry fixes without audit trails, and escalate benign dev proxies as security incidents.

## Research Question

**How can Windows endpoint reliability failures be classified, evidenced, and governed through reproducible proof tiers and policy-gated remediation?**

## Contribution

1. **Evidence model** linking signals to proof tiers (T0–T5) with upgrade guards
2. **Classification taxonomy** for twelve primary proxy/reliability labels with false-positive/false-negative guidance
3. **Policy gates** separating diagnosis from execution authority (preview-only default)
4. **Evaluation harness** with ≥15 controlled scenarios and offline replay benchmarks
5. **Governance artifacts** — hash-chained audit JSONL, committee reports, Power BI star-schema exports

## Methodology

| Phase | Activity |
|-------|----------|
| Observe | Read-only collectors (WinINET, WinHTTP, netstat, optional TLS/browser) |
| Normalize | Fixture-safe JSON evidence packages |
| Classify | Rule engine (`src/platform_core/classification/engine.py`) |
| Prove | Tier resolver + path contrast probes |
| Gate | Policy engine + YAML packs |
| Report | Governance markdown/JSON + analytics CSV |
| Validate | Pytest safety contracts + classifier/replay benchmarks |

## Evidence Model

See [evidence-model.md](evidence-model.md). Pipeline: **Signal → Evidence → Classification → Proof Tier → Policy Gate → Action Preview → Audit Trail → Governance Report**.

## Evaluation Approach

See [evaluation.md](evaluation.md). Harnesses: `classifier-benchmark`, `replay-benchmark`, `tests/evaluation/test_scenario_matrix_15.py`.

## Limitations

See [limitations.md](limitations.md). Windows-first; writer attribution requires optional telemetry; no malware/MITM confirmation; management information only.

## Future Work

- Postgres multi-tenant persistence with row-level security
- Entra ID RBAC integration
- Evidence graph module for cross-endpoint correlation
- Calibrated confidence (beyond ordinal tiers)
- Fleet-scale ingestion at 100k+ endpoints (ADR-008)

## Related Artifacts

- [SYSTEM_DESIGN.md](../SYSTEM_DESIGN.md)
- [case-studies/](case-studies/)
- [adr/ADR-portfolio-positioning.md](adr/ADR-portfolio-positioning.md)

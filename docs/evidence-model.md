# Evidence Model

**Pipeline:** Signal → Evidence → Classification → Proof Tier → Policy Gate → Action Preview → Audit Trail → Governance Report

Canonical implementation: `src/platform_core/evidence/`, `src/platform_core/classification/`, `src/platform_core/policy/`, `src/platform_core/governance/`.

## Platform capabilities

Windows endpoints often fail while still appearing online (proxy errors, dead localhost ports, WinINET/WinHTTP drift). This platform:

1. Collects **deterministic, read-only evidence**
2. Classifies with **proof tiers (T0–T5)** and mandatory **`limitations[]`**
3. Runs **control tests** and **policy gates** (preview-only by default)
4. Produces **audit logs**, **replayable reports**, and **analytics-ready exports**

**AI (when enabled) assists explanation drafting only.** Humans and policy rules authorize execution. See [ai-risk-analyst-guardrails.md](ai-risk-analyst-guardrails.md).

---

## Stage Reference

| Stage | Input | Output | Example | Risk if missing | Auditability |
|-------|-------|--------|---------|-----------------|--------------|
| **Signal** | OS/API reads | Raw observations | `ProxyEnable=1` | Unstructured anecdotes | No replay |
| **Evidence** | Normalized signals | Structured JSON package | `portfolio_evidence.v1` | Conflated observation/proof | Schema versioning |
| **Classification** | Evidence package | Primary label + secondary signals | `DEAD_PROXY_CONFIG` | Wrong triage path | Label + confidence logged |
| **Proof Tier** | Evidence + probes | T0–T5 tier | T2 multi-signal | Over-remediation | Tier in audit row |
| **Policy Gate** | Classification + tier | ALLOW / PREVIEW / BLOCK / … | `PREVIEW_ONLY` | Silent mutation | Policy decision recorded |
| **Action Preview** | Policy allow preview | Dry-run remediation plan | `proxy-disable --dry-run` | Untracked changes | Preview hash in JSONL |
| **Audit Trail** | All stages | Append-only hash chain | `incidents.jsonl` | No accountability | `audit verify` |
| **Governance Report** | Audit + controls | Committee markdown/JSON | [sample_governance_report.md](../reports/sample_governance_report.md) | Oral-only decisions | Limitations mandatory |

---

## Evidence Levels (canonical)

| Level | Meaning | May claim | Must not claim |
|-------|---------|-----------|----------------|
| `OBSERVED_ONLY` | Registry/proxy state read | Settings differ | Who wrote registry |
| `CORRELATED` | Listener/PID alignment | Candidate process | Writer proof |
| `PROVEN_REGISTRY_WRITER` | Sysmon E13 / Procmon | Writer for key | Autonomous containment |
| `PROVEN_NETWORK_IMPACT` | Path failed + writer | App-layer impact | Guaranteed malware |
| `FINAL_CAUSATION` | Writer + port/network | Highest toolkit tier | EDR replacement |

## Rules

- Registry snapshot alone → `OBSERVED_ONLY`
- No upgrade to `PROVEN_*` without writer telemetry
- Confidence is **ordinal**, not probability
- Observation is not proof; correlation is not causation

## Module Map

| Module | Role |
|--------|------|
| `platform_core/evidence/tiers.py` | Tier enums + upgrade guards |
| `platform_core/classification/engine.py` | Label assignment |
| `platform_core/governance/proof_tier.py` | T0–T5 resolver |
| `platform_core/policy/engine.py` | Gate evaluation |
| `platform_core/governance/chain_of_custody.py` | Hash chain |

Tests: `tests/test_evidence_level_contract.py`, `tests/test_observation_not_proof.py`

LAN module: [evidence-boundaries.md](evidence-boundaries.md) · [lan-privacy-monitor.md](lan-privacy-monitor.md)

---

*Legacy path:* [evidence_model.md](evidence_model.md) redirects here.

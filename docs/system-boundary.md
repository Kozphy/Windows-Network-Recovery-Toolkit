# System Boundary

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**ADR:** [adr/0001-system-boundary.md](adr/0001-system-boundary.md)
**Related:** [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md) · [safety-model.md](safety-model.md)

---

## Enterprise problem (boundary context)

Enterprise Windows endpoints can **drift away from approved network baselines** — dead localhost proxies, WinINET/WinHTTP stack mismatches, TLS path divergence — causing connectivity failures, inconsistent troubleshooting, control exceptions, and **weak audit evidence** when teams reset registry settings without structured proof.

This repository addresses **evidence → decision → gated action → verification → audit** for that problem class. It does **not** replace enterprise security products or management judgment.

---

## The system IS responsible for

| Responsibility | Implementation status | Evidence |
|----------------|----------------------|----------|
| Collecting endpoint network/proxy evidence | **Implemented** | `windows_network_toolkit/collectors/`, `proxy_state.py` |
| Normalizing signals into structured events | **Implemented** | Evidence tiers, governance envelope |
| Detecting configuration deviations | **Implemented** | Classification engine, purple detection rules |
| Running deterministic control tests | **Implemented** | `control_tests.py`, CTRL-001–010 |
| Calculating risk indicators (ordinal, not probabilistic) | **Implemented** | Classifier confidence, purple metrics |
| Recommending remediation actions | **Implemented** | Remediation planner, preview packages |
| Policy-gating destructive actions | **Implemented** | `safety.py`, `src/platform_core/policy/engine.py` |
| Producing remediation **previews** (dry-run default) | **Implemented** | `proxy_remediation.py`, API dry-run defaults |
| Post-remediation verification (where implemented) | **Implemented** | `src/proxy_guard/verification.py`, purple verification |
| Maintaining hash-chained audit records | **Implemented** | `src/platform_core/audit/writer.py` |
| Purple Team control validation (fixture-driven) | **Prototype** | `src/purple_team/` — CI uses fixtures only |
| Governance / committee reporting exports | **Prototype** | Sample reports, Power BI blueprint |

---

## The system IS NOT responsible for

| Exclusion | Rationale |
|-----------|-----------|
| Replacing management or audit judgment | Outputs are decision **support**, not approvals |
| Autonomous high-risk regulatory decisions | No auto-apply without typed human confirmation |
| Guaranteeing security or eliminating risk | Epistemic boundaries enforced in CI |
| Replacing Internal Audit or external auditors | Management information only — not formal opinions |
| Malware detection or EDR functions | Explicit non-claim — reliability triage labels only |
| Executing irreversible actions without authorization | Process kill, firewall reset, adapter disable **blocked** |
| Proving registry writer identity without telemetry | Writer proof requires Sysmon E13 / Procmon — not bundled |
| Fleet-wide signed agent deployment at scale | Fleet simulate is synthetic; no production MSI |
| WORM / SIEM / immutable off-host custody | Local JSONL + tip anchor only |
| Live adversary emulation in CI | Purple scenarios are fixture-simulated |

---

## Automation vs decision support vs human approval

```text
┌─────────────────────────────────────────────────────────────────┐
│  HIGH-FREQUENCY + DETERMINISTIC          → AUTOMATE (read-only)   │
│  Examples: proxy-status, control tests, audit append, classify   │
├─────────────────────────────────────────────────────────────────┤
│  HIGH-FREQUENCY + AMBIGUOUS            → AUTO + HUMAN REVIEW    │
│  Examples: UNKNOWN_LOCAL_PROXY, POSSIBLE_MITM_RISK triage         │
├─────────────────────────────────────────────────────────────────┤
│  LOW-FREQUENCY + HIGH-RISK               → GOVERNANCE WORKFLOW    │
│  Examples: registry proxy disable apply, purple non-dry-run       │
├─────────────────────────────────────────────────────────────────┤
│  EXCEPTIONAL / EDGE CASE                 → MANUAL EXCEPTION       │
│  Examples: WinHTTP modify (blocked), browser DB writes (blocked)│
└─────────────────────────────────────────────────────────────────┘
```

### Default execution authority

| Action class | Default mode | Human gate |
|--------------|--------------|------------|
| Evidence collection | Auto (read-only) | None |
| Classification | Auto | Review for ambiguous labels |
| Control test execution | Auto | Interpret FAIL with limitations |
| Remediation | **Preview only** | Typed token + explicit `--dry-run false` |
| Purple scenario run (CI) | Fixture simulate | Safety gate + `PURPLE_TEAM_LAB_ONLY` for live |
| Audit logging | Auto append | Verify chain before export |

Governance envelope field: `execution_authority: preview_only` until policy and confirmation allow apply — see `src/platform_core/governance/evidence_to_action.py`.

---

## Trust boundaries

```text
┌───────────────────  Operator / CI Runner  ───────────────────┐
│  CLIs: windows_network_toolkit, src, src.purple_team           │
│  Policy engine · Safety registry · Confirmation tokens         │
└────────────────────────────┬───────────────────────────────────┘
                             │ read-only collectors
                             ▼
┌───────────────────  Windows Endpoint  ─────────────────────────┐
│  Registry (WinINET/WinHTTP) · netstat · optional Sysmon        │
│  NOT modified unless gated apply path explicitly invoked       │
└────────────────────────────┬───────────────────────────────────┘
                             │ structured JSON + JSONL
                             ▼
┌───────────────────  Local Evidence Store  ─────────────────────┐
│  .audit/canonical_custody.jsonl · platform_data/*.jsonl        │
│  Hash chain + tip anchor (local integrity — not WORM)          │
└────────────────────────────┬───────────────────────────────────┘
                             │ export (optional)
                             ▼
┌───────────────────  Reporting / Committee  ──────────────────┐
│  Governance reports · Power BI star schema · FastAPI read API  │
└────────────────────────────────────────────────────────────────┘
```

---

## Capability honesty matrix

| Capability | Status |
|------------|--------|
| Dead proxy detection | **Implemented** |
| Policy-gated proxy disable | **Implemented** (preview default) |
| Hash-chained audit | **Implemented** |
| Purple validation loop | **Prototype** (fixture-first) |
| ETW live ingestion | **Planned** (stub only) |
| Production OAuth/RBAC | **Not supported** (demo headers) |
| Formal SOC 2 / ISO attestation | **Not supported** |

---

## When the boundary should change

Revisit this boundary when:

1. Signed fleet agent and centralized custody are implemented (see `docs/production-readiness-gap.md`).
2. Writer proof telemetry becomes a default deployment requirement.
3. Purple Team moves from fixture-only to lab-gated live mutation with rollback proof.

Until then, position the system as **local-first control-validation and reliability analytics**, not enterprise-wide autonomous remediation.

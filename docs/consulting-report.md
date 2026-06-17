# Technology Risk & Control — Consulting Assessment Report

> **Positioning:** Decision infrastructure for technology risk — not antivirus, EDR, XDR, or autonomous remediation. Heuristic scores support review; they are not automated blocking verdicts.

**Related analytics:** `analytics-summary` CLI · [sql_analytics_queries.md](sql_analytics_queries.md) · Sample: [reports/sample_governance_report.md](../reports/sample_governance_report.md)

**Prepared for:** IT Leadership / Risk Committee  
**Subject:** WinINET proxy drift and localhost listener patterns on corporate endpoints  
**Classification:** Internal — Operational Risk Assessment  
**Date:** June 2026

---

## Executive Summary

Endpoint browsers on a subset of corporate laptops exhibited connectivity failures while basic network tests (ping, DNS) continued to succeed. Investigation **indicates** misconfigured or stale **WinINET proxy settings** — often pointing at localhost ports — as the primary reliability risk driver, rather than upstream network outage.

This assessment documents observed evidence, risk hypotheses, recommended controls, and an operational playbook. Language is intentionally cautious: findings **suggest** likely causes and **require further validation** where registry-writer attribution is unavailable. The toolkit **improves observability** and **supports safer decision-making**; it does **not** fully protect endpoints or guarantee absence of compromise.

---

## Business Problem

| Impact area | Description |
|-------------|-------------|
| Productivity | Users unable to access SaaS, SSO, and internal web applications |
| Support cost | L1/L2 tickets misrouted as "network down" |
| Risk exposure | Manual registry fixes without audit trail or rollback |
| Compliance | Inability to reconstruct who changed proxy settings and when |
| Security ambiguity | Unknown localhost listeners conflated with confirmed threats |

Organizations need a **repeatable, evidence-based triage workflow** that separates observation from proof and gates remediation behind policy.

---

## Technical Background

Windows applications use two common HTTP stacks:

| Stack | Typical consumers | Proxy source |
|-------|-------------------|--------------|
| **WinINET** | Browsers, many desktop apps | HKCU Internet Settings |
| **WinHTTP** | Services, some CLI tools | `netsh winhttp` or direct |

A frequent failure mode: WinINET enables proxy `127.0.0.1:PORT` while WinHTTP remains direct. Ping and DNS succeed; browsers fail. Secondary risk: an **active but unclassified listener** on the configured port — which **indicates** local interception capability but **does not prove** malicious intent without additional telemetry.

---

## Evidence Collected

### Representative observation set (golden case)

| Signal | Value | Evidence tier |
|--------|-------|---------------|
| WinINET ProxyEnable | 1 | Observation |
| WinINET ProxyServer | 127.0.0.1:59081 | Observation |
| WinHTTP | Direct (no proxy) | Observation |
| Listener on 59081 | Not present | Observation |
| Browser HTTPS | Failed | Observation |
| Direct HTTPS path | Succeeded | Observation (contrast) |
| Registry writer | Not identified | Not proven (no Sysmon E13 in scope) |

### Structured proof result

- `localhost_listener_check`: **failed** (no listener)
- `wininet_winhttp_comparison`: **supported** (paths diverge)
- Conclusion: **supported** (ordinal confidence ~0.92)
- Limitations: does not prove malware or MITM

### Unknown listener pattern (secondary case)

| Signal | Value |
|--------|-------|
| ProxyServer | 127.0.0.1:61526 |
| Listener | Present (PID 9999, `unknown_svc.exe`) |
| Registry writer confirmed | No |
| Classification | `UNKNOWN_LOCAL_PROXY` |
| Confidence | Low (~0.35) |

---

## Risk Assessment

| Risk ID | Description | Likelihood | Impact | Inherent risk |
|---------|-------------|------------|--------|---------------|
| R1 | Stale WinINET proxy breaks business apps | Medium | Medium | **Medium** |
| R2 | Unaudited registry remediation | Medium | High | **High** |
| R3 | False threat escalation (listener ≠ writer) | Medium | Medium | **Medium** |
| R4 | Reverter process respawns proxy settings | Low–Medium | Medium | **Medium** |
| R5 | Actual interception via unapproved proxy | Low–Unknown | High | **Requires validation** |

**Residual risk** after recommended controls: **Medium-Low** for R1–R4; R5 remains **requires validation** without writer proof and software inventory correlation.

---

## Root Cause Hypotheses

| Hypothesis | Status | Notes |
|------------|--------|-------|
| H1: Dead localhost proxy in WinINET | **Supported** by structured proof | Primary reliability driver in golden case |
| H2: Network or DNS outage | **Weakened** | Ping/DNS/direct path succeed |
| H3: MITM / TLS interception | **Unproven** in golden case | No TLS mismatch; no active listener |
| H4: Malware persistence | **Requires further validation** | No registry writer proof without telemetry |
| H5: Unapproved local proxy service | **Possible** in listener case | Investigate before containment |

---

## Recommended Controls

| Control | Type | Description |
|---------|------|-------------|
| C1 | Detective | Standardize `proxy-status` and `proxy-watch` in L2 playbook |
| C2 | Preventive | Dry-run default; typed confirmation for registry changes |
| C3 | Corrective | Allowlisted remediation: WinINET disable only (HKCU) |
| C4 | Detective | Append-only audit JSONL with timeline merge |
| C5 | Governance | Incident reports with explicit `limitations[]` |
| C6 | Restrictive | Block silent process kill, firewall reset, adapter disable |
| C7 | Detective | Optional Sysmon E13 for registry writer attribution |

---

## Operational Playbook

### Phase 1 — Observe (read-only)

```powershell
python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit proxy-owner
python -m windows_network_toolkit diagnose --proof
```

### Phase 2 — Classify and document

```powershell
python -m windows_network_toolkit proxy-report
python -m windows_network_toolkit evidence-report --format markdown
```

### Phase 3 — Preview remediation

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

### Phase 4 — Apply (after approval)

```powershell
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

### Phase 5 — Monitor

```powershell
python -m windows_network_toolkit proxy-watch --duration 300 --interval 5
```

### Escalation triggers

- `UNKNOWN_LOCAL_PROXY` with low confidence → security review
- `REVERTER_SUSPECTED` → investigate parent process tree
- `POSSIBLE_MITM_RISK` → TLS proof + certificate store review

---

## Before / After Comparison

| Dimension | Before (ad-hoc scripts) | After (toolkit workflow) |
|-----------|-------------------------|--------------------------|
| Evidence format | Ad-hoc screenshots | Structured JSON + reports |
| Proof vs observation | Often conflated | Tiered evidence model |
| Remediation | Immediate registry edits | Dry-run → confirm → audit |
| Audit trail | None or partial | Append-only JSONL |
| Post-incident replay | Not possible | Deterministic replay |
| Destructive actions | Possible manually | Blocked by policy |
| Risk language | "Confirmed malware" | "Indicates / requires validation" |

---

## Business Impact

| Metric | Expected improvement |
|--------|---------------------|
| Time to consistent diagnosis | Reduced via shared classification |
| Repeat incidents | Reduced via `proxy-watch` reverter detection |
| Audit findings (untracked changes) | Reduced via confirmation + logging |
| False escalations to security | Reduced via limitations and tier gates |
| Training/onboarding | Improved via fixture replay and case studies |

Quantitative baselines should be established per organization; this toolkit **supports measurement** but does not replace ITSM analytics.

---

## Limitations

- Windows-first live probes; non-Windows CI uses fixtures
- Registry writer attribution requires Sysmon E13, Procmon, or equivalent
- Heuristic website/TLS risk scores are for review — not automated blocking
- Does not replace EDR, antivirus, or network perimeter controls
- Confidence scores are ordinal — not statistical probabilities
- Demo API authentication is not production-hardened

---

## Next Steps

1. Pilot toolkit in L2 support with fixture-based training
2. Enable Sysmon E13 collection for proxy registry keys on pilot group
3. Integrate incident JSON reports into ITSM tickets
4. Define escalation SLA for `UNKNOWN_LOCAL_PROXY` and `REVERTER_SUSPECTED`
5. Review CI safety contracts as part of change management for toolkit updates
6. Schedule quarterly replay exercises using golden fixtures

---

*This report uses evidence-based language. Findings indicate likely reliability risks and support safer operations; they do not guarantee endpoint security or prove malicious activity without appropriate telemetry and validation.*

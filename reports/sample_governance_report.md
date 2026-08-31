# Technology Risk & Control — Sample Governance Report

> **Positioning:** Management information for technology risk governance — not a formal audit opinion, SOC 2 report, or security product verdict. Remediation remains **preview-only** by default.

**Prepared for:** IT Leadership / Risk Committee
**Incident ID:** DEMO-DEAD-PROXY-59081
**Subject:** WinINET dead localhost proxy configuration
**Classification (primary):** DEAD_PROXY_CONFIG
**Proof tier:** T2 (multiple independent signals)
**Policy gate:** PREVIEW_ONLY
**Date:** June 2026

---

## Executive Summary

A subset of endpoints exhibited browser connectivity failures while ping and DNS continued to succeed. Structured evidence **indicates** a **dead WinINET proxy configuration** (proxy enabled, localhost port configured, no listener present) with WinHTTP remaining direct. This is a **reliability triage** finding — it **does not prove** malware, confirmed MITM, or compromise.

Recommended action: **preview-only** remediation (WinINET proxy disable) after human review. No silent registry changes, process termination, or firewall reset are authorized by default policy.

---

## Incident Overview

| Field | Value |
| ------- | ------- |
| Endpoint | CORP-LAPTOP-0142 (fixture replay) |
| Symptom | Browser HTTPS failed; ping/DNS OK |
| WinINET ProxyEnable | 1 |
| WinINET ProxyServer | 127.0.0.1:59081 |
| WinHTTP | Direct (no proxy) |
| Listener on 59081 | Not present |
| Registry writer | Not identified (no Sysmon E13 in scope) |

---

## Evidence Collected

| Signal | Value | Tier |
| -------- | ------- | ------ |
| WinINET proxy enabled | Yes | Observation |
| Configured proxy host:port | 127.0.0.1:59081 | Observation |
| WinHTTP proxy path | Direct | Observation |
| Localhost listener check | Failed (no listener) | T1 |
| Direct HTTPS probe | Succeeded | T2 (contrast) |
| Browser HTTPS probe | Failed | Observation |

**Raw evidence references:** tests/fixtures/enert/dead_proxy_59081.json · fixtures/dead_proxy_config/raw_signals.json

---

## Classification

| Attribute | Value |
| ----------- | ------- |
| Primary | DEAD_PROXY_CONFIG |
| Secondary signals | WININET_WINHTTP_MISMATCH, LOCALHOST_PROXY, DEAD_LOCALHOST_PORT |
| Confidence | ~0.92 (ordinal, not probability) |

Classification is **triage**, not causation proof. Observation is not proof.

---

## Proof Tier

| Tier | Meaning in this case |
| ------ | ---------------------- |
| **T2** | Multiple independent deterministic signals agree (config + listener + path contrast) |

T2 supports **preview-only** remediation recommendation. Destructive or invasive actions require higher tiers and explicit human approval per policy.

---

## Policy Decision

| Gate | Outcome |
| ------ | --------- |
| Recommended mode | PREVIEW_ONLY |
| Registry mutation | Requires typed confirmation + audit log |
| Process kill | **BLOCK** (default) |
| Firewall reset | **BLOCK** (default) |
| Adapter disable | **BLOCK** (default) |

Policy separates **diagnosis** from **execution authority**. Humans authorize apply.

---

## Remediation Preview

`powershell
python -m windows_network_toolkit proxy-disable --dry-run
`

Preview output (abbreviated):

- Action: Disable WinINET proxy (HKCU Internet Settings)
- Dry-run: **true** (no registry write)
- Rollback: Re-enable prior ProxyEnable/ProxyServer values from snapshot
- Confirmation required for live apply: DISABLE_WININET_PROXY

---

## Audit Trail

| Artifact | Location |
| ---------- | ---------- |
| Incident JSONL | tests/fixtures/risk_analytics/audit_sample/incidents.jsonl |
| Hash chain | Append-only; verify with audit verify |
| Timeline | proxy-timeline --audit |

Audit entries support **reproducibility** and committee review. Hash-chain verification is a detective control — broken chains must block downstream analytics integrity KPIs.

---

## Limitations

- Windows-first live collection; CI uses deterministic fixtures
- Registry writer attribution requires Sysmon E13 or equivalent — **not proven** in this case
- Does **not** replace EDR, SIEM, ITSM, or enterprise endpoint management
- Does **not** claim malware attribution or MITM confirmation
- Confidence scores are ordinal — not statistical probabilities
- This report is **management information** for governance discussion, not a formal audit opinion

---

## Recommended Next Steps

1. Run diagnose --proof and attach structured JSON to ITSM ticket
2. Obtain L2 approval before live proxy-disable
3. Enable Sysmon E13 on pilot group for writer attribution
4. Schedule proxy-watch if reverter behavior is suspected
5. Replay incident quarterly using golden fixture for training

---

## Appendix — Raw Evidence References

| Ref | Path | Description |
| ----- | ------ | ------------- |
| A1 | fixtures/dead_proxy_config/raw_signals.json | Normalized signal bundle |
| A2 | fixtures/dead_proxy_config/expected_classification.json | Expected classifier output |
| A3 | fixtures/dead_proxy_config/expected_policy.json | Expected policy gate |
| A4 | examples/evidence/DEAD_PROXY_CONFIG.json | Portfolio evidence schema v1 |

---

*Findings indicate likely endpoint reliability risks and support safer operational decisions. They do not guarantee endpoint security or prove malicious activity without appropriate telemetry and validation.*

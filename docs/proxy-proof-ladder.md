# Proxy Proof Ladder — T0 through T5

**Status:** Normative claim-strength ladder for WinINET proxy investigations  
**Modules:** `evidence_schema.EvidenceTier`, `proxy_state_machine.build_proxy_evidence_event`, `proof.py`  
**Principle:** Each rung adds **evidence type**, not automatic **authorization to accuse or remediate**.

---

## Ladder overview

```text
T5 GOVERNANCE_PROOF     Human-confirmed apply logged in audit
T4 WRITER_PROOF         Registry writer telemetry (Sysmon E13, Procmon)
T3 PATH_EVIDENCE        Direct vs proxy HTTPS/TCP probes
T2 RUNTIME_EVIDENCE     Listener/process on configured port
T1 STATE_EVIDENCE       WinINET/WinHTTP registry configuration read
T0 OBSERVATION          Unstructured note or uncorroborated log line
```

**Rule:** Never skip rungs in audit narrative. Never describe T2 as T4.

---

## T0 — Observation

### Definition

A fact recorded without structured normalization or corroboration.

### Examples

- Operator note: "Browser broken after VPN disconnect"
- Raw proxy-watch log line without state diff
- Screenshot of registry editor

### What it proves

That someone observed or recorded something.

### What it does NOT prove

Configuration truth, path behavior, writer identity, or remediation safety.

### Module behavior

Below T1 — not emitted by standard normalizers unless explicitly tagged.

---

## T1 — State evidence

### Definition

Structured read of WinINET/WinHTTP configuration at a point in time.

### Examples

- `proxy-status` → `ProxyEnable=1`, `ProxyServer=127.0.0.1:59081`
- `proxy_change` event: `ProxyServer 127.0.0.1:59081 → (none)`
- Transition: `PROXY_SERVER_REMOVED` with empty after_server

### Case study: dead proxy (config only)

**Observation:** WinINET enabled toward `127.0.0.1:59081`.  
**Tier:** T1 — config read only.  
**Allowed language:** "WinINET points to localhost port 59081."  
**Blocked language:** "Dead proxy confirmed" (needs T3 path evidence).

### Module mapping

- `normalize_proxy_state` → `T1_STATE_EVIDENCE`
- `normalize_proxy_change_event` → `T1_STATE_EVIDENCE`
- Default transition proof tier (no listener) → T1

---

## T2 — Runtime evidence

### Definition

Runtime corroboration: process listening, port bind, or co-temporal signals.

### Examples

- `proxy-owner`: `node.exe` listening on 59081
- Transition with `LISTENER_PRESENT` secondary signal
- `tcp_listening=true` on configured port

### Case study: dev tooling (Cursor / Node)

**Observation:** WinINET → `127.0.0.1:9222`; listener `cursor.exe` or `node.exe`.  
**Tier:** T2 — correlation.  
**Allowed language:** "Process cursor.exe correlated with configured localhost port."  
**Blocked language:** "Cursor wrote registry" (needs T4).

**Trusted dev tools note:** `TRUSTED_DEV_TOOLS` in state machine lowers risk band for known tooling — still correlation, not writer proof.

### Case study: listener missing

**Observation:** Proxy enabled toward 59081; no listener.  
**Tier:** T2 signal `LISTENER_MISSING`.  
**Supports:** Dead proxy hypothesis when combined with T3.

### Module mapping

- `normalize_listener_state` → T2 (T4 if `writer_proof` or Sysmon E13)
- Transition with listener → proof_tier T2 for localhost enable/reverter classes

---

## T3 — Path evidence

### Definition

Structured network path contrast — direct vs proxied connectivity.

### Examples

- `proxy-health`: `direct_probe_ok=true`, `proxy_probe_ok=false`, `proxy_status=DEAD_LOCALHOST_PROXY`
- `DIRECT_VS_PROXY_PATH_COMPARISON` control FAIL
- `diagnose --proof` with supported dead-proxy hypothesis

### Case study: dead WinINET proxy (full triage)

**T1:** ProxyEnable=1, ProxyServer=127.0.0.1:59081  
**T2:** No listener on 59081  
**T3:** Direct HTTPS OK; proxy path fails  
**Classification:** `DEAD_PROXY_CONFIG`  
**Allowed language:** "Evidence consistent with dead localhost proxy blocking browser traffic."  
**Blocked language:** "Malware disabled the listener."

### Case study: WinINET / WinHTTP mismatch

**T1:** WinINET proxied; WinHTTP direct access flag set  
**T3:** Browser path differs from system stack expectations  
**Classification:** `WININET_WINHTTP_MISMATCH`  
**Control:** CTRL-002 FAIL

### Module mapping

- `normalize_probe_result` → `T3_PATH_EVIDENCE`
- Proof engine attempts: `direct_connectivity_check`, `proxied_connectivity_check`

---

## T4 — Writer proof

### Definition

Telemetry identifying **who wrote** proxy registry keys — not merely who listens.

### Examples

- Sysmon Event ID 13 with process image and target object
- Procmon registry write stack
- Security Event 4657 (when configured)

### Case study: unknown local proxy escalation

**T2:** Unknown process on localhost port  
**T4:** Sysmon E13 shows `malware.exe` wrote `ProxyServer`  
**Allowed language:** "Registry writer attributed to process X via Sysmon E13."  
**Blocked language:** "Proved attacker intent" or "Proved malware" (intent ≠ writer proof).

### Without T4

Owner control returns **PARTIAL** — `WRITER_LIMITATION` applies.

### Module mapping

- `normalize_listener_state` with `writer_proof=true` → T4
- `build_attribution` with `writer_kind` in sysmon/procmon/eventlog

---

## T5 — Governance proof

### Definition

Human operator confirmed remediation (or explicit policy action) recorded in hash-chained audit.

### Examples

- Operator typed `DISABLE_WININET_PROXY` and apply logged
- Audit row: `execution_authority: human_confirmed`
- Policy decision `confirmed: true` in Power BI fact table

### Case study: remediation after review

**T3:** Dead proxy confirmed  
**Policy:** PREVIEW_ONLY → human review → typed confirmation  
**T5:** Apply logged with rollback snapshot reference  
**Allowed language:** "Operator confirmed proxy disable per policy."  
**Blocked language:** "Automated remediation succeeded."

### Module mapping

- `fact_policy_decisions.confirmed=true`
- Platform tier `T4_OPERATOR_CONFIRMED` in governance report

---

## Reverter pattern (cross-tier)

### Case study: reverter suspected

**T1:** Repeated enable/disable of localhost proxy in watch timeline  
**T2:** Listener may appear intermittently  
**Pattern:** `detect_reverter_loop_pattern` → `REVERTER_SUSPECTED_LOCALHOST_PROXY_LOOP`  
**Tier label:** T2 for pattern; **not T4** without registry writer trace  
**Control:** CTRL-007 FAIL  
**Recommendation:** Collect Sysmon E13; do not auto-kill process

---

## Ladder misuse (audit findings)

| Misuse | Correction |
|--------|------------|
| "T2 proves malware" | T2 proves correlation — full stop |
| "Proof supported → safe to disable" | Proof supports hypothesis — policy gate still required |
| "No T4 needed for production fix" | T4 needed for **attribution**, not always for reliability fix |
| Collapsing T1+T3 into "final causation" | Use bounded language until T4/T5 where applicable |

---

## Quick reference table

| Tier | Question answered | Typical command |
|------|-------------------|-----------------|
| T0 | What was noted? | Manual notes |
| T1 | What is configured? | `proxy-status` |
| T2 | What is running on the port? | `proxy-owner` |
| T3 | Does traffic work direct vs proxy? | `proxy-health`, `diagnose --proof` |
| T4 | Who wrote registry? | Sysmon / Procmon integration |
| T5 | Who authorized apply? | Audit JSONL + typed confirmation |

---

## Related documents

- [audit-evidence-model.md](audit-evidence-model.md)
- [proof-vs-observation.md](proof-vs-observation.md)
- [portfolio-case-study-1-dead-wininet-proxy.md](portfolio-case-study-1-dead-wininet-proxy.md)
- [portfolio-case-study-3-reverter-suspected.md](portfolio-case-study-3-reverter-suspected.md)

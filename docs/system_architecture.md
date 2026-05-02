# System Architecture

For the **Failure Knowledge System** pipeline (signals → FailureBlock → JSONL → CLI/API → human repair), see **[`architecture.md`](architecture.md)**.

This document describes how the toolkit is structured as a layered troubleshooting system, not just a collection of scripts.

## 1) High-Level Architecture

```text
User Problem
   |
   v
auto_diagnose.bat
   |
   v
Evidence Collection Layer
   |  (ping, DNS, TCP 443, HTTPS, proxy, connection signals)
   v
Root Cause Classifier
   |  (classify_root_cause.bat)
   v
Fix Recommendation Engine
   |  (recommend_fix.bat; safest action first)
   v
Repair Scripts
   |  (reset_dns.bat / reset_proxy.bat / one_click_fix.bat)
   v
Logs and User Output
   |  (console guidance + logs/network_diagnosis_*.txt)
   v
Retest and Observe
```

## 2) Layered Diagnostic Model

The toolkit follows a layered network model so failures can be isolated step by step.

### Layer 1: Network Reachability

- Primary signal: `ping 8.8.8.8`
- Question: can the host reach the internet path at basic IP level?
- Typical outcome: if this fails, troubleshooting should start with adapter/router/ISP path.

### Layer 2: DNS Resolution

- Primary signal: `nslookup google.com`
- Question: can domain names resolve into IP addresses?
- Typical outcome: if ping works but DNS fails, low-risk DNS fix should be attempted first.

### Layer 3: TCP and HTTPS Path

- Primary signals:
  - `Test-NetConnection google.com -Port 443`
  - `curl https://www.google.com`
- Questions:
  - is TCP 443 reachable?
  - does HTTPS traffic complete?
- Typical outcome: distinguishes path/filtering issues from lower-layer connectivity.

### Layer 4: Application Layer (Browser Behavior)

- Primary signal: browser behavior compared with CLI checks
- Question: does browser fail while network checks succeed?
- Typical outcome: browser-specific settings, extensions, or per-app configuration.

### Layer 5: System Resource Pressure

- Primary signals:
  - `TIME_WAIT` and `ESTABLISHED` trends
  - process-level connection concentration
  - dynamic TCP port range context
- Question: is connection churn or socket pressure causing delayed failures?
- Typical outcome: detect potential connection exhaustion and guide code/process remediation.

## 3) Decision Flow: Data -> Diagnosis -> Decision -> Action

The toolkit intentionally separates each stage:

1. Data collection
   - Scripts collect objective runtime evidence.
2. Diagnosis
   - Rule-based scripts convert signals into likely root-cause categories.
3. Decision
   - Recommendation layer ranks safest next action first.
4. Action
   - User runs a targeted repair, or a fallback full repair only when needed.

This design avoids "reset everything first" behavior and improves repeatability for support and debugging.

## 4) Key Design Principles

### Safe by default

- Diagnosis and observability scripts are read-only.
- Fix scripts are explicit and user-invoked.
- No automatic destructive repair execution.

### Minimal repair first

- Lower-risk targeted fixes are prioritized before full stack reset.
- Recommendation engine labels risk level and explains why.

### Separation of concerns

- Evidence collection, classification, recommendation, monitoring, and repair are separate scripts.
- Each script has a clear responsibility and can be used independently.

### Beginner-friendly output

- Output is structured with status, interpretation, and next steps.
- Users are guided with plain language, not raw command output only.

## 5) LinkedIn-Ready Summary

I built a Windows network recovery toolkit that turns messy connectivity symptoms into a layered diagnosis and decision workflow. Instead of only printing command output, it collects evidence, classifies likely root causes, recommends the safest next fix, and adds real-time observability for connection behavior. The project demonstrates system thinking, practical debugging under uncertainty, and real-world problem solving through automation that remains beginner-friendly and safe by default.

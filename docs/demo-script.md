# 3-Minute Demo Script — Technology Risk & Endpoint Reliability

**Audience:** Technology Risk Analyst, Cyber Risk Consultant, IT Audit, Platform Reliability  
**Duration:** ~3 minutes (fixture-safe on any OS)  
**Safety:** Read-only / preview-only — no host mutation

---

## Setup (15 seconds)

```powershell
cd Windows-Network-Recovery-Toolkit
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

**Say:** “Ping works but the browser fails — a common endpoint reliability problem that creates technology risk when teams disagree on cause and fix.”

---

## 1. Symptom — browser failure, network looks fine (20 seconds)

Show screenshot or describe: `ERR_PROXY_CONNECTION_FAILED` on LinkedIn/Edge while ping/DNS succeed.

**Say:** “This is not automatically malware — it’s often proxy stack drift.”

---

## 2. Proxy status + classification (30 seconds)

```powershell
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
```

**Point out:**

- `DEAD_PROXY_CONFIG` primary classification  
- `WININET_WINHTTP_MISMATCH` secondary signal  
- `limitations[]` — does not prove MITM  
- `governance` envelope — `claim_strength`, `execution_authority: preview_only`

---

## 3. WinINET vs WinHTTP mismatch (25 seconds)

```powershell
python -m windows_network_toolkit diagnose --proof --fixture examples/evidence/WININET_WINHTTP_MISMATCH.json
```

**Say:** “WinINET drives browsers; WinHTTP drives many services. Divergence explains asymmetric failures.”

---

## 4. Proof command (25 seconds)

```powershell
python -m windows_network_toolkit proxy-proof --url https://example.com
# On non-Windows or offline: use fixture path above
```

**Say:** “Proof contrasts direct vs proxied paths — observation upgraded to supported hypothesis for config issues, not compromise.”

---

## 5. Evidence report (30 seconds)

```powershell
python -m windows_network_toolkit evidence-report --url https://example.com `
  --fixture tests/fixtures/enert/dead_proxy_59081.json --format markdown
```

**Show:** Executive summary, timeline, confidence model, safety disclaimer.

Sample: [examples/reports/dead_proxy_config_report.md](../examples/reports/dead_proxy_config_report.md)

---

## 6. Audit JSONL (20 seconds)

```powershell
python -m windows_network_toolkit governance-report `
  --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

**Say:** “Every step is auditable — hash-chained JSONL, KPI rollups, governance reports for risk committees.”

---

## 7. Business / risk value (15 seconds)

**Close with:**

> “This platform turns noisy endpoint incidents into evidence-backed risk assessments, control tests, remediation **previews**, and audit-ready governance reports — without pretending to be EDR or autonomous remediation.”

**Portfolio:** [PORTFOLIO.md](../PORTFOLIO.md) · **Architecture:** [architecture.md](architecture.md)

---

## Optional extensions

| Scenario | Fixture |
|----------|---------|
| Dev proxy (not malicious) | `examples/evidence/LOCAL_PROXY_ACTIVE.json` |
| Reverter / intermittent | `make proxy-intermittent` (Windows, 15 min soak) |
| MITM triage | `examples/evidence/POSSIBLE_MITM_RISK.json` |

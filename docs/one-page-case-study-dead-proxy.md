# One-Page Case Study — Dead Localhost WinINET Proxy

**Case ID:** `CASE_1_DEAD_WININET_PROXY` · **Fixture:** `tests/fixtures/case_studies/case_1_dead_wininet_proxy.json`

---

## Symptom

- Browser shows `ERR_PROXY_CONNECTION_FAILED` or SSO timeouts  
- `ping` and DNS succeed — endpoint appears “online”  
- User blames Wi-Fi, VPN, or “virus” without evidence  

---

## Evidence collected (read-only)

| Source | Observation |
|--------|-------------|
| WinINET | `ProxyEnable=1`, `ProxyServer=127.0.0.1:59081` |
| WinHTTP | Direct access enabled (stack mismatch) |
| Listener | **No process** on port 59081 |
| Health probe | Direct HTTPS OK; proxy path **failed** |

**Proof tier:** T2 (registry state + path probe) — not registry writer proof (T5).

---

## Classification

| Field | Value |
|-------|-------|
| Primary | `DEAD_PROXY_CONFIG` |
| Secondary signals | `WININET_WINHTTP_MISMATCH`, `LOCALHOST_PROXY`, `DEAD_LOCALHOST_PORT` |
| Confidence | 0.92 (ordinal ranking — not probability) |

**Human interpretation:** Evidence indicates browser traffic is routed to a dead localhost proxy. This creates **endpoint reliability risk**. It does **not** prove malware, compromise, or malicious intent.

---

## Control test result

| Control | Result | Note |
|---------|--------|------|
| `WININET_LOCALHOST_PROXY_HEALTH` | **FAIL** | Enabled localhost proxy with failed path |
| `DIRECT_VS_PROXY_PATH_COMPARISON` | **FAIL** | Direct OK, proxy fail |
| `SAFE_REMEDIATION_POLICY` | **PASS** | Remediation remains preview-only |

---

## Policy decision

| Field | Value |
|-------|-------|
| Action | `DISABLE_WININET_PROXY` |
| Outcome | `PREVIEW_ONLY` |
| Requires confirmation | `DISABLE_WININET_PROXY` typed token |
| Dry-run default | **true** |

No autonomous registry mutation. Operator must explicitly confirm live apply.

---

## Audit trail

- State snapshots → `.audit/proxy-watch.jsonl` (append-only)  
- Hash chain verifiable via `audit verify`  
- Governance rollup: `governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample`  

---

## Limitations (required disclosure)

- Does not prove **who** changed the registry (no Sysmon E13 in this fixture)  
- Does not prove **malware** or **MITM**  
- Disabling proxy may be wrong if corporate PAC is required — human review  
- Confidence is **ordinal**, not calibrated probability  

---

## Business value

| Stakeholder | Value |
|-------------|-------|
| IT Support | Structured diagnosis instead of blind registry reset |
| Security | Triage without false malware accusation |
| Audit | Replayable evidence + control test artifacts |
| Risk committee | KPI export via Power BI star schema |

---

## Demo commands

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit proxy-disable --dry-run --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

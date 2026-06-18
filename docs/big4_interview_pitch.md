# Big 4 Interview Pitch

## Business problem

IT, Security, Compliance, and Audit disagree on **cause** and **allowed remediation** when endpoints fail (proxy drift, TLS mismatch, unknown listeners). Scripts fix symptoms; risk teams need **evidence quality**, **control testing**, and **audit-ready reporting**.

## Technical solution

Technology Risk & Control Analytics Platform:

- Evidence tiers + proof engine (`diagnose --proof`)
- Control tests + policy-gated remediation preview
- Hash-chained audit + `governance-report` / `risk-kpi-summary`
- Evidence-to-Action governance model (six principles)

## Control framework mapping

[NIST CSF 2.0 + ISO-style themes](framework_mapping.md) — partial support, honestly marked.

## Audit-ready evidence

- JSONL audit trail, `audit verify`
- Governance reports with limitations[]
- Sample risk register and KPI fixtures

## Business impact

Ordinal business impact estimates for triage — not financial advice ([business_impact_model.md](business_impact_model.md)).

## Limitations

- Not antivirus, EDR, XDR, SIEM replacement
- Not autonomous remediation
- Classification is not accusation
- MITRE ATT&CK = triage context only

## What I learned

- Separating **observation**, **correlation**, and **proof** prevents overclaim in incident narratives.
- **Policy permission ≠ safety** — dry-run and typed confirmation must be enforced in code and tests.
- Risk analytics needs **honest KPIs** with limitations, not fake precision.

## Quick commands

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit risk-kpi-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit governance-report --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json --format markdown
```

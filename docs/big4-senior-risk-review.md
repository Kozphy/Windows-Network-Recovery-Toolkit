# Big 4 senior technology risk review

For technology risk / IT audit advisory interviews. **Management information only** — not a formal audit opinion.

## Control narrative

| Control theme | Implementation | Evidence |
|---------------|----------------|----------|
| Logging & monitoring | Hash-chained audit JSONL + Postgres `AuditChainEntry` | `audit verify`, `/v1/audit/verify` |
| Change management | Policy-gated remediation previews | `control_tests`, policy registry |
| Access control | `/v1` RBAC roles | [rbac-model.md](rbac-model.md) |
| Human oversight | `review_required` + human review module | [human-review-workflow.md](human-review-workflow.md) |

## Proof tiers (T0–T5)

Classifications carry `proof_tier` and `limitations[]` — accusatory-adjacent classes route to human review, not auto-escalation to "compromise."

## Committee reporting

- `GET /v1/reports/executive` — KPIs from DB
- Power BI star schema — `analytics/powerbi/`
- Sample: [reports/sample_governance_report.md](../reports/sample_governance_report.md)

## Abuse cases mapped to threat model

[security-abuse-cases.md](security-abuse-cases.md) ↔ [threat-model.md](threat-model.md)

## Explicit non-claims (repeat in interview)

- Not EDR, not malware detection, not MITM confirmation
- Not autonomous remediation
- Not calibrated probability of compromise
- Not cross-platform fleet agent at enterprise scale

## Demo script

```powershell
make prod-demo-up
curl -H "X-Api-Token: dev-trisk-token" -H "X-Api-Role: auditor_readonly" http://127.0.0.1:8000/v1/reports/executive
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

## Gap defense

[production-gap-defense.md](production-gap-defense.md) · [production-readiness-scorecard.md](production-readiness-scorecard.md)

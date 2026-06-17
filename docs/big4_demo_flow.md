# Big 4 Interview Demo — 5-Minute Script

Fixture-safe demo for screen share or in-person interviews. No admin rights required.

**Setup:**

```powershell
cd Windows-Network-Recovery-Toolkit
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

---

## Step 1 — Business objective and control matrix (30 sec)

**Say:** "Before touching commands, I frame the engagement: business objective is reliable browser access; asset is WinINET proxy configuration; threat is dead localhost proxy; controls include drift detection, policy-gated remediation, and audit trail."

**Show:** [technology_risk_control_matrix.md](technology_risk_control_matrix.md) — row 1 (browser access reliability).

---

## Step 2 — Observation (`proxy-status`)

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Say:** "This is **observation**, not proof. We read WinINET proxy enabled toward `127.0.0.1:59081`, WinHTTP direct, classification `DEAD_PROXY_CONFIG`. We're recording what we saw — not claiming causation yet."

**Point to JSON:** `classification`, `secondary_signals`, `limitations`.

---

## Step 3 — Proof envelope (`diagnose --proof`)

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Say:** "This upgrades evidence through structured tests: localhost listener check failed, WinINET/WinHTTP comparison supported. Conclusion is **supported** with explicit limitations — we still do not claim malware or MITM."

**Point to JSON:** `proof_attempts`, `conclusion.status`, `limitations`.

---

## Step 4 — Risk assessment (`risk-assess`)

```powershell
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

**Say:** "This translates technical evidence into **risk and governance language**: business objective, asset, threat, findings, inherent/residual risk rating, and governance decision."

**Point to JSON:** `risk_rating`, `governance_decision`, `findings`.

---

## Step 5 — Control test (`control-test`)

```powershell
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

**Say:** "This is how a consultant or internal auditor tests whether controls are operating — drift detection fails as expected, proof envelope passes, remediation safety passes because we're dry-run preview-only."

**Point to JSON:** `control_tests` — `CT_PROXY_DRIFT`, `CT_REMEDIATION_SAFETY`.

---

## Step 6 — Management report (`governance-report`)

```powershell
python -m windows_network_toolkit governance-report --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json --format markdown
```

**Say:** "This is the **audit-ready management artifact** — executive summary, findings, risk table, control test results, governance decision, and limitations."

---

---

## Step 7 — Policy-gated remediation (`proxy-disable --dry-run`)

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

**Say:** "No destructive action by default. Remediation is **preview-only** unless policy allows apply, operator provides typed confirmation, rollback plan is reviewed, and audit logging is enabled. Policy permission is not a safety guarantee."

**Point to JSON:** `outcome`, `dry_run`, `requires_confirmation`.

---

## Step 8 — Analytics KPI summary (optional, 30 sec)

```powershell
python -m windows_network_toolkit analytics-summary --audit-dir tests/fixtures/analytics/audit_sample --format markdown
```

**Say:** "For data and risk analyst audiences, we can roll up audit JSONL into KPI distributions — classifications, evidence tiers, policy outcomes, blocked destructive actions — with explicit limitations."

---

## Optional closing (15 sec)

**Say:** "The platform is decision infrastructure — not EDR, not autonomous remediation. The same workflow applies to FinTech API outages, TLS issues, and configuration drift at scale."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | `$env:PYTHONPATH = (Get-Location).Path` |
| Fixture not found | Use full path or short name `case_1_dead_wininet_proxy.json` |
| `proxy-disable` on Linux | Expected — returns `unsupported_platform`; explain dry-run contract still applies on Windows |

---

## Related

- [interview_pitch_5_minutes.md](interview_pitch_5_minutes.md)
- [three-minute-demo-script.md](three-minute-demo-script.md)

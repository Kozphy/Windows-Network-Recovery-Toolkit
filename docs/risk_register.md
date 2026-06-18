# Risk Register

Ordinal risk register for portfolio demonstrations. **Not** a production GRC system export.

**Sample fixture:** `tests/fixtures/risk_register/sample_risk_register.json`

## Fields

| Field | Description |
|-------|-------------|
| `risk_id` | Unique identifier |
| `risk_title` | Short risk name |
| `asset_or_process` | Affected asset or process |
| `risk_scenario` | Scenario narrative (evidence-backed language) |
| `evidence_sources` | CLI commands / audit sources |
| `likelihood_score` | Ordinal 1–5 (not probability) |
| `impact_score` | Ordinal 1–5 |
| `inherent_risk` | low / medium / high |
| `control_effectiveness` | partial / effective / ineffective |
| `residual_risk` | After controls |
| `risk_owner` | Remediation owner |
| `remediation_action` | Policy-gated next step |
| `due_date` | Target date |
| `status` | open / mitigated / accepted |
| `limitations` | Epistemic and scope limits |

## Usage

```powershell
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

Risk register summary is embedded when sample fixture is present.

# Case Study CS1: WinINET Proxy Drift (Dead Localhost Proxy)

Golden case for principle compliance validation.

## Validate principles

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit principles validate --fixture case_studies/cs1_wininet_proxy_drift/fixture.json
python -m windows_network_toolkit diagnose --proof --principles --fixture case_studies/cs1_wininet_proxy_drift/fixture.json
python -m windows_network_toolkit proxy-report --include-principles --fixture case_studies/cs1_wininet_proxy_drift/fixture.json
```

## Files

| File | Purpose |
|------|---------|
| `fixture.json` | Full incident payload |
| `timeline.jsonl` | Drift timeline |
| `expected_classification.json` | Expected DEAD_PROXY_CONFIG output |
| `expected_principle_compliance.json` | All four principles must pass |
| `report.md` | Human-readable report |

## Principles enforced

1. Observation is not proof — remediation requires proof envelope
2. Correlation is not causation — dead port ≠ malicious writer
3. Confidence is not certainty — ordinal 0.92, not probability
4. Policy permission is not safety — dry-run, confirmation, rollback, audit required

See [docs/case-study-1-proxy-drift.md](../../docs/case-study-1-proxy-drift.md).

# Demo Cases

## Golden demo (5 min)

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
make demo
```

Expected:

- Replays `windows_network_toolkit/examples/proxy_drift_incident.jsonl`
- Markdown report with executive summary, timeline, policy gate
- JSON artifact at `logs/golden_demo_report.json`
- Dashboard URL printed (start `make demo-api` separately)

## Bad gateway

```powershell
python -m windows_network_toolkit bad-gateway-diagnose --url https://www.microsoft.com
```

Use `--json-only` for machine output.

## Audit verify

```powershell
python -m toolkit audit verify logs/canonical_decision_audit.jsonl
```

## Safety contract tests

```powershell
pytest -q tests/test_policy_safety_contract.py tests/platform_core/policy
```

# 5-minute demo

Read-only, no admin, no host mutation.

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
make demo
```

This replays `windows_network_toolkit/examples/proxy_drift_incident.jsonl`, runs the policy gate, and prints a markdown audit report.

**Dead-proxy golden path (fixtures, no host mutation):**

```powershell
python -m windows_network_toolkit proxy-status --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit diagnose --proof --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit proxy-disable --dry-run --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit governance-report --fixture fixtures/dead_proxy_config/raw_signals.json --format markdown
```

**LAN executive report (fixture):**

```powershell
python -m windows_network_toolkit risk-executive-report --fixture examples/lan/executive_bundle.json --format both
```

Extended catalog: [demo-commands-reference.md](demo-commands-reference.md) · Panel demo: [interview-demo-3min.md](interview-demo-3min.md)

| Step | Command |
|------|---------|
| **Golden demo** | `make demo` |
| Bad gateway diagnose | `python -m windows_network_toolkit bad-gateway-diagnose --url https://example.com` |
| Audit verify | `python -m toolkit audit verify logs/canonical_decision_audit.jsonl` |
| API + dashboard | `make demo-api` then open http://127.0.0.1:8000/dashboard/ |
| Healthy scenario | `make demo-healthy` |
| Proxy drift | `make demo-proxy-drift` |

Each `demo-scenario` emits **Markdown + JSON** (`--format both`), including:

- evidence level
- policy decision
- recommended next step
- explicit limitations
- deterministic replay summary + fingerprint

```powershell
python -m src demo-scenario final-causation --format both
python -m src demo-scenario proxy-drift --format json
```

No admin privileges required. Fixtures only — no host mutation.

Epistemic boundaries: observation ≠ proof · correlation ≠ causation · PREVIEW ≠ execute approval.

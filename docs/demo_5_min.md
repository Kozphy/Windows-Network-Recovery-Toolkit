# 5-minute demo

Read-only, no admin, no host mutation.

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

| Step | Command |
|------|---------|
| Healthy | `make demo-healthy` |
| Proxy drift (correlated) | `make demo-proxy-drift` |
| Final causation | `make demo-final-causation` |
| Fleet 100×20 | `make demo-fleet-enterprise` |
| Full portfolio | `make demo-production` |

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

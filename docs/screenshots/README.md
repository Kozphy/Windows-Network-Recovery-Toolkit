# Screenshots & Demo Assets

Add portfolio screenshots here before publishing to GitHub or LinkedIn.

## Recommended captures

| File (placeholder) | What to capture |
|------------------|-----------------|
| `01-browser-proxy-error.png` | Browser `ERR_PROXY_CONNECTION_FAILED` with ping terminal beside it |
| `02-proxy-status-json.png` | `proxy-status --fixture dead_proxy_59081.json` highlighting classification |
| `03-diagnose-proof.png` | `diagnose --proof` output with `proof_attempts` and `limitations` |
| `04-proxy-disable-dry-run.png` | `proxy-disable --dry-run` showing preview, not execution |
| `05-proxy-report.png` | Incident report JSON or rendered markdown |
| `06-evidence-timeline.png` | `proxy-timeline` or replay output |
| `07-dashboard.png` | `http://127.0.0.1:8000/dashboard/` operator view |
| `08-ci-green.png` | GitHub Actions CI workflow passing |

## Recording tips

- Use fixture commands for portable demos (no admin required)
- Font size 14+ in terminal
- Highlight `limitations[]` in every JSON screenshot
- Blur hostnames, usernames, and real IP addresses

## Generate locally

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

See [demo-video-script.md](../demo-video-script.md) for full recording flow.

# Case 1: Dead WinINET Proxy

## Symptom

Browsers fail with `ERR_PROXY_CONNECTION_FAILED` while `ping` and `nslookup` succeed.

## Observation

| Signal | Value | Tier |
|--------|-------|------|
| WinINET `ProxyEnable` | `1` | OBSERVED_ONLY |
| WinINET `ProxyServer` | `127.0.0.1:59081` | OBSERVED_ONLY |
| Listener on port 59081 | not found | OBSERVED_ONLY |
| WinHTTP | direct access | OBSERVED_ONLY |

## Hypothesis

Dead WinINET localhost proxy — browser path broken, base network likely OK.

## Evidence

- Registry proxy enabled pointing at localhost high port
- No listener bound on configured port
- WinINET/WinHTTP path mismatch

## Proof level

**Supported** (ordinal ~0.92) — listener check failed; path comparison supported. **Not** malware or MITM proof.

## Policy decision

`DISABLE_WININET_PROXY` → **PREVIEW_ONLY** — typed confirmation required; dry-run default.

## Remediation preview

```json
{"dry_run": true, "no_changes_made": true, "planned_changes": ["ProxyEnable=0", "Clear ProxyServer"]}
```

## Limitations

- Does not prove who wrote registry values
- Does not prove malware or MITM
- Listener classification is correlation, not writer proof

## Audit trail

Chain fields: `event_id`, `timestamp`, `source=proxy-status`, `evidence_tier=OBSERVED_ONLY`, `classification=DEAD_PROXY_CONFIG`, `policy_decision=PREVIEW_ONLY`, `hash`, `previous_hash`

## Interview explanation

> "Ping works but browsers don't — I treat that as a path problem. We classify dead localhost proxy, run structured proof, preview WinINET disable behind policy gates, and document what we cannot prove."

## Demo commands

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-status --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit proxy-disable --dry-run
python -m windows_network_toolkit fleet-simulate --fixture tests/fixtures/fleet/fleet_100_endpoints.jsonl
```

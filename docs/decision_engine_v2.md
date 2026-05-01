# Decision engine v2 (live hypotheses)

## Inputs

`LiveNetworkSnapshot` merges:

- Existing `FeatureVector` probes (`src/diagnostics/collector.py`)
- HKCU proxy normalization + localhost proxy parsing
- Optional localhost listener attribution + netstat-derived counters
- Interesting process rows sampled from CSV `tasklist`

## Hypotheses (deterministic)

All scores stay in `[0,1]` additive bumps with clamp:

- `unexpected_user_proxy`
- `local_proxy_hijack`
- `browser_proxy_path_issue`
- `localhost_proxy_owner_suspicious`
- `socket_exhaustion`
- `dns_resolution_issue`
- `tls_path_issue`
- `winhttp_proxy_issue`
- `winsock_corruption_possible`
- `isp_router_path_issue`

## Compatibility

Historic `python -m src diagnose` (v1) remains untouched; **`diagnose-live`** writes `reports/last_diagnosis_live.json` and richer JSONL without replacing v1 payloads.

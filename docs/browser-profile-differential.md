# Browser-profile differential diagnostics

## Purpose

Diagnose sites that **fail in a normal Chromium profile** but **work in InPrivate/Incognito**, while raw OS probes still succeed.

Pipeline: **Observation → Hypothesis → Proof → Policy → Preview → Audit → Replay**

## Why private success matters (and what it does not prove)

If a site works in InPrivate/Incognito and a cookie-free raw probe succeeds, that **reduces the probability** of a Windows-wide DNS, TCP, TLS, or system-proxy failure — but it **does not prove** those layers are universally healthy for every path/policy.

## Primary commands

```powershell
$env:PYTHONPATH = (Get-Location).Path

# HAR differential (recommended offline proof)
python -m windows_network_toolkit browser-diff https://www.104.com.tw/ --browser edge --proof `
  --import-normal-har normal.har --import-private-har private.har

# Fixture replay
python -m windows_network_toolkit browser-diff https://www.104.com.tw/ `
  --fixture tests/fixtures/browser_profile/104_profile_fail.json --format text

# Profile metadata (no cookie values)
python -m windows_network_toolkit browser-profile inspect --browser edge
python -m windows_network_toolkit browser-profile site-state 104.com.tw --browser edge
python -m windows_network_toolkit browser-profile repair-preview 104.com.tw --browser edge
```

`wnrt` is an alias for the same CLI when installed editable.

## Evidence modes

| Mode | Description |
|------|-------------|
| A — HAR compare | User exports HARs from normal vs private windows |
| B — Controlled Playwright | Ephemeral vs toolkit test profile (optional `[browser]` extra); labeled as reproduction, not user-profile proof |
| C — Read-only profile inspect | Copies Chromium SQLite; cookie **metadata** only |

## Example: recruitment site (104.com.tw)

**Symptom:** Site fails in normal Edge; works in InPrivate; `curl`/raw probe OK.

**Finding (fixture):** `OS_NETWORK_OK_BROWSER_PROFILE_FAIL` with probable site-data / auth redirect loop.

**Safe next step:** Delete **only** `104.com.tw` site data / unregister that domain's service workers — not a full profile reset.

## Privacy

Never logs cookie values, Authorization headers, passwords, history, or encryption keys. See [har-redaction.md](har-redaction.md) and [browser-repair-safety.md](browser-repair-safety.md).

## API (read-only / preview)

- `GET /trisk/browser/diff`
- `GET /trisk/browser/profiles`
- `GET /trisk/browser/site-state`
- `GET /trisk/browser/extensions`
- `GET /trisk/browser/policies`
- `POST /trisk/browser/har/compare`
- `POST /trisk/browser/repair/preview`

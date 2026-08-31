# Audit custody (Level 1 + tip anchor)

Local-first **hash-chained** audit with an optional **tip anchor** file for stronger
tamper detection. This is **not** WORM storage, SIEM, or formal assurance.

## Paths

| Artifact | Default path | Override |
| ---------- | -------------- | ---------- |
| Canonical custody JSONL | `.audit/canonical_custody.jsonl` | `WNT_AUDIT_DIR` |
| Tip anchor | `.audit/canonical_custody.tip.json` | sibling of JSONL, or `--tip-path` |

Legacy operator logs (e.g. `logs/proxy_guardian.jsonl`) remain for compatibility.
Guardian / proxy-fix / ensure-proxy-health **dual-write** into the canonical chain.

## Tip anchor

After each hash-chained append, the writer refreshes:

```json
{
  "schema_version": "audit_tip_anchor.v1",
  "anchored_at_utc": "…",
  "audit_path": ".audit/canonical_custody.jsonl",
  "tip_hash": "<last current_hash>",
  "record_count": 12
}
```

- **Chain verify** — JSONL hashes are internally consistent
- **Tip match** — last `current_hash` equals the tip file (detects full-file rewrite if tip was not updated)

Same-directory tip is defense-in-depth only. Relocate or sign tips for stronger custody.

## Commands

```powershell
$env:PYTHONPATH = (Get-Location).Path

# Hash chain only
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl

# Chain + tip
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip

# Fail if tip missing
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --require-tip
```

## Modules

| Module | Role |
| -------- | ------ |
| `src/platform_core/audit/writer.py` | Hash-chained append + tip refresh |
| `src/platform_core/audit/tip_anchor.py` | Tip write / load / verify |
| `src/platform_core/audit/custody.py` | Proxy/ensure event mapping into custody |
| `src/platform_core/audit/paths.py` | `WNT_AUDIT_DIR` resolution |

## Limitations

- Observation ≠ proof; tip match ≠ immutability
- Confirmation **tokens are never stored** — only `confirmation_supplied: true/false`
- Soft-fail on custody write errors so remediation is not blocked by disk issues

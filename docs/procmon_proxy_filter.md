# Procmon filter set — WinINET proxy registry writes

Ship a narrow Process Monitor filter so CSV exports feed toolkit writer-proof import
(`proxy-attribution --procmon`, `proxy-watch --evidence-csv`).

**This is observation of registry writes in a Procmon capture window — not malware
attribution, and not a guarantee that every rewrite was captured.**

## Quick start

```powershell
# Print Filter → Add recipe
python -m src procmon-filter-set

# Machine-readable copy (also shipped at telemetry/procmon/…)
python -m src procmon-filter-set --json
python -m src procmon-filter-set --export .\my-filter.json
```

Canonical asset: [`telemetry/procmon/wininet_proxy_regsetvalue.filter.json`](../telemetry/procmon/wininet_proxy_regsetvalue.filter.json)

## Filter rules (Process Monitor)

1. Start **Procmon as Administrator**.
2. **Filter → Filter…** (Ctrl+L).
3. Add **Include** rules:

   | Column | Relation | Value |
   | -------- | ---------- | ------- |
   | Operation | is | `RegSetValue` |
   | Path | contains | `Internet Settings\ProxyEnable` |
   | Path | contains | `Internet Settings\ProxyServer` |
   | Path | contains | `Internet Settings\AutoConfigURL` |
   | Path | contains | `Internet Settings\ProxyOverride` |
   | Path | contains | `Internet Settings\AutoDetect` |

4. Enable **Drop Filtered Events**.
5. Reproduce the rewrite (browser / scheduled task / wait for reverter).
6. **File → Save → CSV** with columns: Time of Day, Process Name, PID, Operation, Path, Result, Detail.

## Import into the toolkit

```powershell
python -m src proxy-attribution --procmon .\procmon_proxy.csv --json
python -m src proxy registry-writer-proof --json --procmon-csv .\procmon_proxy.csv
```

Pair with a short soak while Procmon is capturing:

```powershell
python -m src proxy-watch --interval 3 --soak-minutes 2 --exit-on-rewrite
```

## Epistemic boundaries

| Claim | Status |
| ------- | -------- |
| Procmon row shows process X wrote `ProxyEnable` | Strong local **writer evidence** (within capture limits) |
| Process listening on `127.0.0.1:N` wrote the key | **Correlation only** unless Sysmon/Procmon agrees |
| Intent / malware family | **Out of scope** for this toolkit |

See [proxy_writer_attribution.md](proxy_writer_attribution.md), [telemetry_registry_writer_proof.md](telemetry_registry_writer_proof.md), [adr/ADR-004-heuristic-attribution-is-not-proof.md](adr/ADR-004-heuristic-attribution-is-not-proof.md).

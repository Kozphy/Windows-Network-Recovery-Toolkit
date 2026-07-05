# Router Evidence Mode

Import router exports for **correlated** home/SOHO LAN analytics.

## Supported imports

| `--type` | Input formats | Normalized fields |
|----------|---------------|-------------------|
| `dns` | CSV, JSON array | `client_ip`, `domain`, `timestamp_utc` |
| `firewall` | CSV | `src_ip`, `dst_ip`, `port`, `action` |
| `dhcp` | CSV, JSON | `mac`, `ip`, `hostname`, `lease_utc` |
| `devices` | JSON array | `mac`, `ip`, `name` |

## CLI

```powershell
python -m windows_network_toolkit router-import --type dns --input examples/router/dns_queries.csv --out .audit/router-dns.jsonl
python -m windows_network_toolkit router-correlate --host-log .audit/lan-watch.jsonl --router-log .audit/router-dns.jsonl
```

## Correlation

Joins router DNS/DHCP with host inventory by **IP/MAC**. Output includes:

- `matched_dns` — queries tied to known inventory devices
- `unmatched_dns` — queries without host cache match
- `highest_evidence_source` — `ROUTER_LEVEL_EVIDENCE` when imports present

## Limitations

- Import is **read-only** on source files
- Vendor-specific router APIs are out of scope (export files only)
- Correlation does not prove device intent or data exfiltration

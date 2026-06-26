# LAN Privacy Monitor

Home/SOHO **Technology Risk / Control Analytics** module for observed local network discovery and device inventory.

## Positioning

- Observes LAN discovery activity from a **Windows host** (and optional **router imports**)
- Does **not** confirm spying, malware, data theft, or advertising surveillance
- **Observation ≠ proof** — scanning ≠ malicious intent

## Commands

```powershell
python -m windows_network_toolkit lan-inventory --json-only
python -m windows_network_toolkit lan-watch --duration 120 --interval 10
python -m windows_network_toolkit lan-mdns-summary --duration 15
python -m windows_network_toolkit lan-ssdp-summary --duration 15
python -m windows_network_toolkit lan-privacy-report --fixture executive_bundle.json --format both
python -m windows_network_toolkit lan-risk-score --fixture executive_bundle.json
python -m windows_network_toolkit lan-control-test --fixture executive_bundle.json
python -m windows_network_toolkit router-import --type dns --input ../router/dns_queries.csv --out .audit/router-dns.jsonl
python -m windows_network_toolkit router-correlate --host-log .audit/lan-watch.jsonl --router-log .audit/router-dns.jsonl
python -m windows_network_toolkit risk-executive-report --fixture executive_bundle.json --format both
```

Fixture paths resolve under `examples/lan/` and `examples/router/`.

## Classifications

| Label | Meaning |
|-------|---------|
| `NORMAL_DISCOVERY` | Benign SOHO discovery patterns |
| `NEW_DEVICE_OBSERVED` | New neighbor in inventory |
| `FREQUENT_DISCOVERY` | High broadcast rate (may include smart TVs) |
| `BROAD_SUBNET_PROBING` | Multi-target probe pattern |
| `POSSIBLE_LATERAL_RECON` | Broad ICMP/SYN pattern — needs router/PCAP evidence |
| `UNKNOWN_IOT_DEVICE` | Unknown vendor with active discovery |
| `INSUFFICIENT_EVIDENCE` | Too few events for confident label |

## Demo fixtures

| File | Scenario |
|------|----------|
| `examples/lan/normal_home_network.jsonl` | Normal home |
| `examples/lan/smart_tv_frequent_discovery.jsonl` | Smart TV SSDP/mDNS |
| `examples/lan/unknown_broad_probing.jsonl` | Subnet probing |
| `examples/lan/router_evidence_unavailable.jsonl` | Sparse host-only |
| `examples/lan/executive_bundle.json` | Full executive assessment |

## Related docs

- [evidence-boundaries.md](evidence-boundaries.md)
- [privacy-risk-score.md](privacy-risk-score.md)
- [lan-control-matrix.md](lan-control-matrix.md)
- [router-evidence-mode.md](router-evidence-mode.md)

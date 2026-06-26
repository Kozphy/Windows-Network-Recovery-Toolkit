# Evidence Boundaries — LAN & Platform

Cross-cutting rules for what each evidence source may support.

## Evidence sources

| Source | May observe | Must not claim |
|--------|-------------|----------------|
| `HOST_LEVEL_OBSERVATION` | ARP/neighbor cache, mDNS/SSDP on segment, traffic to/from this PC | Cross-host port scans, exfiltration proof |
| `ROUTER_LEVEL_EVIDENCE` | DHCP roster, DNS queries, firewall rows per import | Packet contents, malware verdict |
| `PACKET_CAPTURE_EVIDENCE` | Flow summaries from PCAP fixtures (v1) | Full payload inspection without capture |
| `INSUFFICIENT_EVIDENCE` | Sparse telemetry only | Any elevated risk narrative |

## Core principles

1. **Observation ≠ proof**
2. **Scanning ≠ malicious intent**
3. **Suspicious ≠ confirmed compromise**
4. **Attribution requires additional evidence**

## Safe language

Use: *observed*, *possible*, *consistent with*, *requires additional evidence*, *cannot confirm exfiltration from Windows host telemetry alone*.

Never: *confirmed spying*, *confirmed data theft*, *confirmed malware*, *confirmed advertising surveillance*.

## Upgrade rules

- Host observations **cannot** be narrated as router-grade outbound proof without `ROUTER_LEVEL_EVIDENCE`.
- DNS domain patterns are **risk weighting**, not malware classification.
- Executive reports include explicit **what this tool cannot prove** sections.

See also: [evidence-model.md](evidence-model.md), [lan-privacy-monitor.md](lan-privacy-monitor.md).

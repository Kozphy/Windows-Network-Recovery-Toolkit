# LAN Control Matrix — CTRL-LAN-001..008

| ID | Objective | Pass | Fail signal |
|----|-----------|------|-------------|
| CTRL-LAN-001 | Maintain asset inventory | ≥2 devices with IP/MAC | Empty inventory |
| CTRL-LAN-002 | Detect unauthorized devices | No unknown unapproved devices | Unknown vendor without DHCP cross-check |
| CTRL-LAN-003 | Review IoT outbound DNS | DNS logs + IoT devices | IoT without DNS import |
| CTRL-LAN-004 | Segment IoT from work | Segmentation or no co-mingling | IoT + work on same segment indicators |
| CTRL-LAN-005 | Disable unnecessary discovery | Normal discovery volume | Excessive unknown discovery |
| CTRL-LAN-006 | Review UPnP exposure | UPnP reviewed or absent | SSDP/UPnP without review |
| CTRL-LAN-007 | Retain router logs | Router JSONL imported | No router evidence |
| CTRL-LAN-008 | Investigate subnet probing | No broad probing class | BROAD_SUBNET_PROBING / POSSIBLE_LATERAL_RECON |

Each control includes remediation text prefixed **Consider (preview only):** — no autonomous changes.

Implementation: `windows_network_toolkit/lan_control_tests.py`

```powershell
python -m windows_network_toolkit lan-control-test --fixture examples/lan/executive_bundle.json
```

Catalog YAML: `config/controls/lan_privacy_controls.yaml`

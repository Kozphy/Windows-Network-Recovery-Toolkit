# Network Segmentation Advisor

**Recommendation-only** guidance for home/SOHO LAN privacy. Does not modify router or Windows settings.

## Rules

| Trigger | Recommendation |
|---------|----------------|
| Unknown IoT + work devices | Guest Wi-Fi / VLAN for IoT |
| Smart TV + laptop, no segmentation proof | Separate work from casting devices |
| UPnP/SSDP observed | Review UPnP; disable if unnecessary |
| No router logs | Enable DNS filtering / router logging |
| Broad subnet probing | Investigate; consider isolating source device |

## Output

`SegmentationAdvice` objects with `priority`, `rationale`, `limitations`, `preview_only: true`.

Included in `risk-executive-report` output under `segmentation_advice`.

Implementation: `windows_network_toolkit/diagnostics/lan_privacy/segmentation_advisor.py`

# Benchmark Dataset Schema

The benchmark uses JSON Lines (`.jsonl`). One row represents one independently scored scenario or one scored point in a temporal trace.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `scenario_id` | string | Stable unique scenario identifier |
| `scenario_family` | string | Group used for stratification and leakage control |
| `source_class` | enum | `synthetic`, `controlled`, or `real_world` |
| `ground_truth_drift` | boolean | Frozen reference label |
| `ground_truth_basis` | string | How ground truth was established |
| `predictions` | object | Mapping of method name to boolean prediction |

## Optional temporal fields

| Field | Type | Meaning |
|---|---|---|
| `trace_id` | string | Identifier shared by observations in one trace |
| `observed_at_ms` | integer | Observation time relative to trace start |
| `event_start_ms` | integer | Known drift-event start time |
| `detection_at_ms` | object | Mapping of method name to first detection time |

## Optional analysis fields

- `windows_version`
- `policy_profile`
- `wininet_state`
- `winhttp_state`
- `dns_context`
- `tls_context`
- `limitations`
- `provenance`

## Example

```json
{"scenario_id":"syn-0001","scenario_family":"dead-localhost-proxy","source_class":"synthetic","ground_truth_drift":true,"ground_truth_basis":"fixture construction","predictions":{"naive":true,"static":true,"context":true}}
```

## Data governance rules

- Do not place credentials, hostnames, usernames, IP addresses, or other unnecessary identifying endpoint data in research fixtures.
- `real_world` rows must be sanitized and accompanied by provenance/limitations.
- Labels must be frozen before final evaluation.
- Rows from one underlying incident must share a `scenario_family` or trace grouping suitable for leakage-aware resampling.

# SRE interview walkthrough

**Pitch:** Local-first endpoint reliability platform with SLO metrics derived from append-only JSONL — not a hosted SIEM.

## 5-minute arc

1. **Symptom:** proxy drift detected (`platform_signals.jsonl`)
2. **MTTD:** `mean_time_to_detect_seconds` from occurred_at → detected_at
3. **MTTE:** `mean_time_to_explain_seconds` through explained_at (timeline + causation)
4. **Fleet scale:** `fleet-simulate --endpoints 25` — fixture-only
5. **SLO dashboard:** `GET /platform/slo` + Grafana `/metrics`
6. **Incident review:** human-readable postmortem from case studies

## SLO fields

- `proxy_drift_incidents_total`
- `blocked_high_risk_action_count`
- `remediation_preview_count`
- `proof_unavailable_rate` / `final_causation_rate`
- `remediation_stickiness_rate` (case study 003)

## Talking points

- Preview-only remediation; execute requires admin + confirmation
- False positive rate tracked when incidents marked `false_positive`
- Stickiness failure → escalate, do not blind re-execute

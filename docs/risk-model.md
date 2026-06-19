# Technology Risk Scoring Model

**Status:** Phase 1 — `windows_network_toolkit/risk_scoring_engine.py`  
**Positioning:** Ordinal governance input for human review — **not** malware verdicting, EDR scoring, or autonomous remediation authority.

---

## Pipeline placement

```text
Evidence → Incident Classification → Proof tier → Control Testing → Risk Scoring → Human Review → Audit → Executive Report
```

| Stage | Module | Output |
|-------|--------|--------|
| Classification | `incident_classifier.py` | `incident_class`, `confidence`, `risk_level` (triage) |
| Control testing | `control_tests.py` | PASS / FAIL / PARTIAL / NOT_TESTED per control |
| **Risk scoring** | `risk_scoring_engine.py` | `likelihood`, `impact`, `risk_score`, `risk_level`, `explanation` |
| Human review | `RiskDecisionRecord` (governance) | Reviewer attestation |
| Executive report | `reporting.py` | `technology_risk_executive_report.v1` |

---

## Inputs (`RiskScoringInput`)

| Field | Type | Description |
|-------|------|-------------|
| `incident_class` | string | Primary classification label (e.g. `DEAD_PROXY_CONFIG`) |
| `evidence_quality` | float 0–1 | Ordinal confidence from classifier |
| `proof_level` | string | T0–T4 tier or `NOT_RUN` |
| `business_impact` | string | `low` \| `medium` \| `high` \| `critical` |
| `recurrence_count` | int | Repeat observations in audit window |
| `control_test_result` | string | Worst-case aggregate: PASS / FAIL / PARTIAL / NOT_TESTED |

---

## Outputs (`RiskScoringResult`)

| Field | Description |
|-------|-------------|
| `likelihood` | `low` \| `medium` \| `high` — ordinal, not probability |
| `impact` | Business impact band |
| `risk_score` | 0–100 composite for sorting and dashboards |
| `risk_level` | `LOW` \| `MEDIUM` \| `HIGH` (thresholds: 40, 70) |
| `explanation` | Human-readable scoring rationale |
| `limitations` | Mandatory governance caveats |
| `human_review_recommended` | True when HIGH or control FAIL |

---

## Scoring logic (summary)

1. **Class base** — high-risk classes (`DEAD_PROXY_CONFIG`, `REVERTER_SUSPECTED`, …) elevate likelihood.
2. **Evidence quality** — classifier `confidence` weights observation strength.
3. **Proof tier** — T4 writer proof weighs higher than T0–T1 correlation.
4. **Recurrence** — +5% likelihood per repeat, capped at +20%.
5. **Controls** — FAIL adds +25% likelihood modifier; PASS subtracts 15%.
6. **Composite** — `risk_score = likelihood_raw × impact_score × 20`, capped at 100.

---

## Relationship to other risk modules

| Module | When to use |
|--------|-------------|
| `risk_scoring_engine.py` | **Endpoint analytics pipeline** — incidents + control tests from JSONL/fixtures |
| `src/platform_core/risk/risk_rating.py` | **Fixture case studies** — governance reports with mature control catalog |
| `incident_classifier.risk_level` | Fast triage label before full scoring |
| `backend/engine.py` | Legacy SaaS diagnose heuristic — unrelated to governance scoring |

Do not merge formulas without an explicit adapter — each serves a different evidence grain.

---

## Governance principles (enforced in `limitations[]`)

1. Observation is not proof.  
2. Correlation is not causation.  
3. Confidence is not certainty.  
4. Classification is not accusation.  
5. Policy permission is not safety guarantee.  
6. Automation must not silently change registry, firewall, adapter, or process state.

---

## CLI and API

```powershell
# Risk scores included in analytics pipeline output
python -m windows_network_toolkit analytics-summary --fixture tests/fixtures/analytics_pipeline_fixture.json --json

# Executive JSON report export
python -c "import json; from pathlib import Path; from windows_network_toolkit.analytics_pipeline import run_endpoint_analytics_pipeline; from windows_network_toolkit.reporting import export_technology_risk_report; p=run_endpoint_analytics_pipeline(fixture=json.loads(Path('tests/fixtures/analytics_pipeline_fixture.json').read_text())); export_technology_risk_report(p, Path('examples/reports'))"
```

```text
GET /risks              — paginated risk scores
GET /reports/executive  — executive governance JSON
GET /trisk/health       — technology risk API health (root /health = ERP platform)
```

See also: [architecture.md](architecture.md) · [powerbi-schema.md](powerbi-schema.md)

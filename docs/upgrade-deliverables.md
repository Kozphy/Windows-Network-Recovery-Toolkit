# Technology Risk Platform Upgrade — Deliverables

## Summary of changes

Upgraded repository positioning to a **research-grade Technology Risk & Control Analytics Platform** with canonical documentation, demo fixture packs, evaluation harness (15 scenarios), CLI aliases, proof-tier T5 mapping, and sample governance/Power BI artifacts.

## Files created

| Path | Purpose |
|------|---------|
| `docs/research-framing.md` | Research abstract, methodology, future work |
| `docs/evidence-model.md` | Signal → governance pipeline |
| `docs/classification-taxonomy.md` | Per-label FP/FN and policy guidance |
| `docs/proof-tiers.md` | T0–T5 + remediation permissions |
| `docs/policy-gates.md` | Gate definitions and classification map |
| `docs/evaluation.md` | 15-scenario evaluation plan |
| `docs/limitations.md` | Limitations register |
| `docs/safety-model.md` | Canonical safety doctrine |
| `docs/msc-application-summary.md` | MSc / SOP text (150–500 words) |
| `docs/test-control-matrix.md` | CTRL → pytest mapping |
| `fixtures/*/raw_signals.json` (+ 3 expected files each) | Six demo fixture packs |
| `tests/fixtures/evaluation/scenarios_15.json` | Golden evaluation scenarios |
| `tests/evaluation/test_scenario_matrix_15.py` | Parametrized scenario tests |
| `tests/evaluation/test_ctrl_matrix_regression.py` | CTRL-001–010 anchors |
| `tests/platform_core/governance/test_proof_tier_resolver.py` | T0–T5 resolver tests |
| `tests/integration/test_governance_report_integrity.py` | Chain + report wording |
| `tests/fixtures/risk_analytics/audit_sample_chained/` | Valid hash-chained JSONL |
| `src/platform_core/classification/adapters.py` | Legacy label normalization |
| `src/platform_core/policy/outcome_normalizer.py` | Policy gate normalization |
| `windows_network_toolkit/architecture.py` | Module map |
| `analytics/powerbi/schema.md` | Star schema reference |
| `analytics/powerbi/sample_csv/` | Sample CSV export |
| `scripts/generate_fixture_packs.py` | Fixture pack generator |
| `reports/sample_governance_report.md` | Committee sample (UTF-8) |

## Files modified

- `README.md` — subtitle, MSc audience, golden demo commands
- `docs/DOCUMENTATION_INDEX.md` — canonical research pack
- `docs/interview-demo-3min.md` — timed 0:00–3:00 script
- `docs/classification-model.md`, `evidence_model.md`, `policy_model.md`, `safety_model.md` — legacy redirects
- `examples/powerbi/report_blueprint.md` — redirect stub
- `src/platform_core/governance/proof_tier.py` — T5 + evidence tier mapping
- `windows_network_toolkit/cli.py` — `diagnose --proof`, `replay-demo`, `export-powerbi` aliases

## Demo commands

```powershell
pip install -r requirements.txt
python -m windows_network_toolkit diagnose --proof --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit evidence-report --fixture fixtures/dead_proxy_config/raw_signals.json --format markdown
python -m windows_network_toolkit replay-demo --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
python -m windows_network_toolkit audit verify tests/fixtures/risk_analytics/audit_sample_chained/incidents.jsonl
python -m windows_network_toolkit export-powerbi --audit-dir tests/fixtures/risk_analytics/audit_sample_chained --out-dir analytics/powerbi/sample_csv
```

## Test commands

```powershell
pytest -q tests/evaluation/
pytest -q tests/platform_core/governance/test_proof_tier_resolver.py
pytest -q tests/test_policy_safety_contract.py
ruff check .
pytest -q
```

## Remaining limitations

- Windows-first live collectors; CI relies on fixtures
- Three parallel vocabularies remain at boundaries (adapters normalize; full enum unification deferred)
- `analytics-export-powerbi` flat CSV names differ from star-schema `fact_*` names
- No Postgres RLS, Entra ID, or evidence graph module (blueprint only)
- Formal audit opinions and malware/MITM confirmation explicitly out of scope

## Suggested next upgrades

1. Unify classification enums across `incident_classifier` and enterprise YAML
2. Postgres multi-tenant persistence + RLS
3. Evidence graph module under `src/platform_core/graph/`
4. Embed latest classifier/replay benchmark results in `docs/evaluation.md`
5. Entra ID RBAC for `/v1/enterprise` routes

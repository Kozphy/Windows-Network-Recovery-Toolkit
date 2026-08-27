# Evaluation Protocol

1. Load scenarios from `scenarios/` (schema-validated).  
2. Safety gate (dry-run allowed; live requires authorization).  
3. Simulate from fixtures under `tests/fixtures/purple_team/`.  
4. Normalize telemetry with provenance + evidence hash.  
5. Run modular detection rules.  
6. Score risk (documented heuristic weights).  
7. Recommend response (execution separate).  
8. Fixture remediation only when authorized / approved.  
9. Independent verification of post-conditions.  
10. Compute confusion + operational metrics.  
11. Emit tamper-evident evidence bundle.  

Repro:

```bash
python -m src.purple_team benchmark --no-evidence --json
python -m src.purple_team baselines
```

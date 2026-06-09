# Evidence model

Canonical levels (`platform_core/evidence_model.py`):

| Level | Meaning | May claim | Must not claim |
|-------|---------|-----------|----------------|
| `OBSERVED_ONLY` | Registry/proxy state changed | Settings differ from baseline | Who wrote registry |
| `CORRELATED` | Listener/PID/parent match | Candidate process | Registry writer proof |
| `PROVEN_REGISTRY_WRITER` | Sysmon E13 / Procmon / ETW | Writer process for key | Autonomous containment |
| `PROVEN_NETWORK_IMPACT` | Browser path failed + writer proof | App-layer impact | Guaranteed malware |
| `FINAL_CAUSATION` | Writer + port owner or network impact | Highest toolkit tier | EDR replacement |

## Rules

- Registry snapshot alone → `OBSERVED_ONLY`
- Localhost listener alignment → `CORRELATED` at best
- No upgrade to `PROVEN_*` without writer telemetry
- `FINAL_CAUSATION` requires writer proof **and** port-owner or network-impact proof
- Confidence is **ordinal ranking**, not calibrated probability

## Implementation map

| Module | Role |
|--------|------|
| `platform_core/evidence_model.py` | Canonical resolver + upgrade guards |
| `src/proxy_guard/final_causation.py` | Multi-signal fusion reports |
| `src/proxy_guard/registry_writer_proof.py` | Sysmon E13 ingestion |
| `evidence/attribution_engine.py` | Legacy fusion (correlation disclaimers) |

Tests: `tests/test_evidence_level_contract.py`

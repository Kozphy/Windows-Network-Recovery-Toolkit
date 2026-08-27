# Failure Taxonomy

| Category | Meaning |
|---|---|
| SIMULATION_FAILURE | Fixture load / sim stage error |
| TELEMETRY_MISSING | Required events absent |
| COLLECTOR_FAILURE | Collector/normalization failure |
| DETECTION_FALSE_NEGATIVE | Expected detect missed |
| DETECTION_FALSE_POSITIVE | Benign case alerted |
| CLASSIFICATION_ERROR | Risk/class mismatch |
| REMEDIATION_FAILURE | Apply failed |
| VERIFICATION_FAILURE | Post-conditions failed |
| ROLLBACK_FAILURE | Cleanup failed |
| EVIDENCE_INCOMPLETE | Bundle missing stages |
| SAFETY_DENIED | Gate denied execution |
| TELEMETRY_TIMING | Event arrived outside window |

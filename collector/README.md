# Telemetry Collector Bridge

This directory contains a minimal bridge from normalized Windows network signals to the predictive risk API.

The sender intentionally uses Python's standard library so it can run without adding another client dependency.

## Example

Start the API and dashboard:

```bash
uvicorn api.app:app --reload
```

Then send one normalized observation:

```bash
python collector/send_telemetry.py \
  --device-id PC-001 \
  --model xgboost \
  --proxy-mismatch 1 \
  --dns-failure-rate 0.12 \
  --tls-error-count 7 \
  --adapter-reset-count 2 \
  --winhttp-drift 1 \
  --network-profile domain
```

The API will:

1. load the requested trained model artifact,
2. score the observation,
3. derive severity and a governance action,
4. persist the result to the local SQLite risk history,
5. expose the observation to the dashboard through `/api/history`, and
6. include it in the lightweight `/api/drift` indicator.

## Integration point

Production collectors should transform the toolkit's real control evidence into this feature contract rather than hard-code values. Keep collection, feature derivation, prediction, policy, and remediation as separate stages so raw evidence can be audited independently of the model decision.

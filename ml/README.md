# Predictive Technology Risk Modeling

This layer extends the Windows Network Recovery Toolkit from deterministic controls into a hybrid **rules + machine learning + explainability** decision system.

## Architecture

```text
Windows telemetry / control evidence
              |
        feature engineering
              |
   +----------+-----------+
   |          |           |
 Rules   Supervised ML  Anomaly detection
   |          |           |
   |   Logistic / RF /    |
   |   XGBoost / LightGBM |
   |   / CatBoost         |
   |          |           |
   +----------+-----------+
              |
       calibrated risk score
              |
       SHAP explanation
              |
        decision engine
              |
 recovery / escalation / human review
              |
          audit trail
              |
        FastAPI inference API
              |
        browser dashboard
```

## Models

The training pipeline benchmarks:

- Logistic Regression — transparent baseline
- Random Forest — nonlinear baseline
- XGBoost — gradient-boosted trees
- LightGBM — efficient gradient boosting
- CatBoost — strong handling of mixed/categorical data
- Isolation Forest — unsupervised anomaly detection

Optional gradient-boosting packages are discovered at runtime, so the baseline pipeline can still run if one library is unavailable.

## Metrics

Each supervised model is evaluated with:

- Accuracy
- Precision
- Recall
- F1
- ROC-AUC
- PR-AUC
- Brier score for probability quality

Results are written to `ml/artifacts/metrics.json` and models to `*.joblib` files.

## Feature contract

The target column is:

```text
failure_label
```

Example inputs include:

```text
proxy_mismatch
dns_failure_rate
tls_error_count
adapter_reset_count
winhttp_drift
network_profile
```

See `sample_features.csv` for the expected shape. Production telemetry should replace the sample data.

## Quick start

Train the ML layer:

```bash
python -m pip install -r ml/requirements.txt
python ml/train_models.py --data ml/sample_features.csv
```

Run the dashboard/API:

```bash
python -m pip install -r api/requirements.txt
uvicorn api.app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

The same service exposes:

```text
GET  /api/health
GET  /api/models
GET  /api/metrics
POST /api/predict
POST /api/telemetry
GET  /api/history
GET  /api/explainability
GET  /api/drift
GET  /docs
```

The dashboard renders live model artifacts when they exist. If models have not been trained yet, the UI stays available but clearly reports that inference/metrics are unavailable instead of inventing benchmark values.

For a trained tree model:

```bash
python ml/explain_model.py \
  --model ml/artifacts/xgboost.joblib \
  --data ml/sample_features.csv
```

This produces ranked SHAP feature importance in `ml/artifacts/shap_importance.csv`. The dashboard renders that artifact through `/api/explainability`.

## Phase 2 operational intelligence

Successful predictions are now persisted locally to `data/risk_history.sqlite3`, which is already ignored by the repository's runtime-data rules. Each record contains timestamp, device ID, source, model, probability, severity, governance recommendation, approval requirement, and the input evidence fields.

The dashboard adds:

- historical per-device risk trend
- persisted observation count and timestamp
- global SHAP feature-importance bars
- recent-versus-baseline risk drift indicator
- explicit evidence source (`manual` or `telemetry`)
- a live telemetry ingestion contract

A minimal sender is included at `collector/send_telemetry.py`:

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

The collector bridge uses the Python standard library and is intentionally separated from feature collection. Production integration should map real toolkit evidence into this normalized feature contract rather than hard-code values.

## Intended decision flow

The ML score is **evidence**, not an autonomous remediation command. A production integration should combine model probability with existing controls, business impact, confidence, and policy before triggering recovery or escalation.

Recommended downstream record:

```json
{
  "risk_probability": 0.78,
  "rule_severity": "high",
  "top_drivers": ["proxy_mismatch", "tls_error_count"],
  "recommended_action": "verify_network_stack",
  "human_approval_required": true
}
```

## Monitoring boundary

`/api/drift` is a lightweight operational indicator based on recent risk-score movement. It is **not** a formal feature/data-drift detector. Production research should add PSI/KS tests, temporal validation, alert thresholds, and evaluation against known regime changes.

The SHAP panel currently renders global importance exported from a trained tree model. A later phase can add local per-observation SHAP explanations tied to each persisted prediction.

## Frontend capabilities

The dashboard now includes:

- overall risk score and failure probability
- model/severity display
- interactive per-device prediction form
- model benchmark table
- decision recommendation and human-approval state
- API health/model-artifact readiness
- historical risk trend
- drift status
- SHAP importance visualization
- telemetry ingestion example
- responsive desktop/mobile layout

The UI remains dependency-light HTML/CSS/JavaScript served directly by FastAPI. A later productization step can replace it with React/Next.js without changing the API contract.

## Next research upgrades

The next useful additions are probability calibration, temporal validation, formal model/data drift monitoring, local SHAP explanations, survival analysis for time-to-failure, ablation/statistical-significance tests, authentication/RBAC, and direct mapping from the toolkit's real evidence collectors into the feature contract. Those extensions should be driven by real labeled telemetry rather than synthetic benchmark numbers.

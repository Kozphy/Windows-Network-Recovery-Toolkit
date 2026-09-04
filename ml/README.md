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

```bash
python -m pip install -r ml/requirements.txt
python ml/train_models.py --data ml/sample_features.csv
```

For a trained tree model:

```bash
python ml/explain_model.py \
  --model ml/artifacts/xgboost.joblib \
  --data ml/sample_features.csv
```

This produces ranked SHAP feature importance suitable for governance reports and human review.

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

## Next research upgrades

The next useful additions are probability calibration, temporal validation, model/data drift monitoring, survival analysis for time-to-failure, and ablation/statistical-significance tests. Those extensions should be driven by real labeled telemetry rather than synthetic benchmark numbers.

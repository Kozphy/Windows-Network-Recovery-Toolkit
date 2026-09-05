from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_STATE = 42
TARGET = "failure_label"


def _optional_models() -> Dict[str, object]:
    models: Dict[str, object] = {}
    try:
        from xgboost import XGBClassifier

        models["xgboost"] = XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=RANDOM_STATE,
        )
    except ImportError:
        pass

    try:
        from lightgbm import LGBMClassifier

        models["lightgbm"] = LGBMClassifier(
            n_estimators=250,
            learning_rate=0.05,
            num_leaves=31,
            random_state=RANDOM_STATE,
            verbose=-1,
        )
    except ImportError:
        pass

    try:
        from catboost import CatBoostClassifier

        models["catboost"] = CatBoostClassifier(
            iterations=250,
            depth=6,
            learning_rate=0.05,
            random_seed=RANDOM_STATE,
            verbose=False,
        )
    except ImportError:
        pass

    return models


def build_preprocessor(df: pd.DataFrame) -> ColumnTransformer:
    features = df.drop(columns=[TARGET])
    numeric = features.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    categorical = [c for c in features.columns if c not in numeric]

    numeric_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipe, numeric),
            ("cat", categorical_pipe, categorical),
        ]
    )


def evaluate(y_true: pd.Series, prob: np.ndarray) -> dict:
    pred = (prob >= 0.5).astype(int)
    metrics = {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "brier": brier_score_loss(y_true, prob),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, prob)
        metrics["pr_auc"] = average_precision_score(y_true, prob)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train predictive technology-risk models.")
    parser.add_argument("--data", required=True, help="CSV containing failure_label target.")
    parser.add_argument("--out", default="ml/artifacts", help="Artifact output directory.")
    args = parser.parse_args()

    data = pd.read_csv(args.data)
    if TARGET not in data.columns:
        raise ValueError(f"Dataset must contain target column: {TARGET}")

    X = data.drop(columns=[TARGET])
    y = data[TARGET].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y if y.nunique() > 1 else None,
        random_state=RANDOM_STATE,
    )

    preprocessor = build_preprocessor(data)
    models: Dict[str, object] = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        **_optional_models(),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = {}

    for name, model in models.items():
        pipe = Pipeline([("preprocess", preprocessor), ("model", model)])
        pipe.fit(X_train, y_train)
        probability = pipe.predict_proba(X_test)[:, 1]
        results[name] = evaluate(y_test, probability)
        joblib.dump(pipe, out / f"{name}.joblib")

    # Unsupervised anomaly detector complements failure prediction.
    numeric_only = X.select_dtypes(include=[np.number, "bool"]).fillna(0)
    if not numeric_only.empty:
        anomaly = IsolationForest(contamination="auto", random_state=RANDOM_STATE)
        anomaly.fit(numeric_only)
        joblib.dump({"model": anomaly, "columns": numeric_only.columns.tolist()}, out / "isolation_forest.joblib")

    ranking = sorted(results.items(), key=lambda kv: kv[1].get("f1", 0.0), reverse=True)
    report = {"target": TARGET, "models": results, "ranking_by_f1": [name for name, _ in ranking]}
    (out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

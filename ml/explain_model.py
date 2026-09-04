from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SHAP explanations for a trained tree model.")
    parser.add_argument("--model", required=True, help="Path to a saved *.joblib pipeline.")
    parser.add_argument("--data", required=True, help="CSV containing the same feature columns used in training.")
    parser.add_argument("--out", default="ml/artifacts/shap_importance.csv")
    parser.add_argument("--max-rows", type=int, default=500)
    args = parser.parse_args()

    import shap

    pipeline = joblib.load(args.model)
    df = pd.read_csv(args.data).head(args.max_rows)
    if "failure_label" in df.columns:
        df = df.drop(columns=["failure_label"])

    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    transformed = preprocess.transform(df)

    try:
        feature_names = preprocess.get_feature_names_out()
    except Exception:
        feature_names = [f"feature_{i}" for i in range(transformed.shape[1])]

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(transformed)
    if isinstance(values, list):
        values = values[-1]

    import numpy as np

    importance = np.abs(values).mean(axis=0)
    result = pd.DataFrame({"feature": feature_names, "mean_abs_shap": importance}).sort_values(
        "mean_abs_shap", ascending=False
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)
    print(result.head(20).to_string(index=False))


if __name__ == "__main__":
    main()

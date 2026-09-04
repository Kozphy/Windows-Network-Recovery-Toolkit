from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "ml" / "artifacts"

app = FastAPI(
    title="Windows Network Recovery Risk API",
    version="0.1.0",
    description="Read-only inference API for predictive technology-risk models.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    model: str = Field(default="xgboost")
    proxy_mismatch: int = Field(ge=0, le=1)
    dns_failure_rate: float = Field(ge=0)
    tls_error_count: int = Field(ge=0)
    adapter_reset_count: int = Field(ge=0)
    winhttp_drift: int = Field(ge=0, le=1)
    network_profile: str


def _load_metrics() -> dict[str, Any]:
    path = ARTIFACTS / "metrics.json"
    if not path.exists():
        return {
            "status": "not_trained",
            "message": "Train models first to populate ml/artifacts/metrics.json.",
            "models": {},
            "ranking_by_f1": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "artifacts_present": ARTIFACTS.exists(),
        "metrics_present": (ARTIFACTS / "metrics.json").exists(),
    }


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    return _load_metrics()


@app.get("/api/models")
def models() -> dict[str, Any]:
    available = []
    if ARTIFACTS.exists():
        available = sorted(p.stem for p in ARTIFACTS.glob("*.joblib") if p.stem != "isolation_forest")
    return {"models": available}


@app.post("/api/predict")
def predict(payload: PredictionRequest) -> dict[str, Any]:
    model_path = ARTIFACTS / f"{payload.model}.joblib"
    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model artifact not found: {model_path.name}. Train models first.",
        )

    pipeline = joblib.load(model_path)
    features = payload.model_dump(exclude={"model"})
    frame = pd.DataFrame([features])
    probability = float(pipeline.predict_proba(frame)[:, 1][0])

    if probability >= 0.75:
        severity = "high"
        action = "escalate_and_verify_network_stack"
        approval_required = True
    elif probability >= 0.45:
        severity = "medium"
        action = "run_targeted_control_checks"
        approval_required = True
    else:
        severity = "low"
        action = "continue_monitoring"
        approval_required = False

    return {
        "model": payload.model,
        "risk_probability": round(probability, 6),
        "risk_score": round(probability * 100, 1),
        "severity": severity,
        "recommended_action": action,
        "human_approval_required": approval_required,
        "governance_note": "Model output is decision evidence, not an autonomous remediation command.",
    }

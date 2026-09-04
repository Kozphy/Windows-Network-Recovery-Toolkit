from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "ml" / "artifacts"
FRONTEND = ROOT / "frontend"
RUNTIME = ROOT / "data"
HISTORY_DB = RUNTIME / "risk_history.sqlite3"

app = FastAPI(
    title="Windows Network Recovery Risk API",
    version="0.2.0",
    description=(
        "Inference, telemetry history, explainability, and governance API for "
        "predictive technology-risk models."
    ),
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
    device_id: str = Field(default="local-device", min_length=1, max_length=128)
    source: str = Field(default="manual", min_length=1, max_length=64)
    proxy_mismatch: int = Field(ge=0, le=1)
    dns_failure_rate: float = Field(ge=0)
    tls_error_count: int = Field(ge=0)
    adapter_reset_count: int = Field(ge=0)
    winhttp_drift: int = Field(ge=0, le=1)
    network_profile: str


class TelemetryRequest(BaseModel):
    device_id: str = Field(default="local-device", min_length=1, max_length=128)
    model: str = Field(default="xgboost")
    proxy_mismatch: int = Field(ge=0, le=1)
    dns_failure_rate: float = Field(ge=0)
    tls_error_count: int = Field(ge=0)
    adapter_reset_count: int = Field(ge=0)
    winhttp_drift: int = Field(ge=0, le=1)
    network_profile: str


def _connect() -> sqlite3.Connection:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(HISTORY_DB)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observed_at TEXT NOT NULL,
            device_id TEXT NOT NULL,
            source TEXT NOT NULL,
            model TEXT NOT NULL,
            risk_probability REAL NOT NULL,
            risk_score REAL NOT NULL,
            severity TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            human_approval_required INTEGER NOT NULL,
            proxy_mismatch INTEGER NOT NULL,
            dns_failure_rate REAL NOT NULL,
            tls_error_count INTEGER NOT NULL,
            adapter_reset_count INTEGER NOT NULL,
            winhttp_drift INTEGER NOT NULL,
            network_profile TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


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


def _decision(probability: float) -> tuple[str, str, bool]:
    if probability >= 0.75:
        return "high", "escalate_and_verify_network_stack", True
    if probability >= 0.45:
        return "medium", "run_targeted_control_checks", True
    return "low", "continue_monitoring", False


def _predict(payload: PredictionRequest) -> dict[str, Any]:
    model_path = ARTIFACTS / f"{payload.model}.joblib"
    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model artifact not found: {model_path.name}. Train models first.",
        )

    pipeline = joblib.load(model_path)
    features = payload.model_dump(exclude={"model", "device_id", "source"})
    frame = pd.DataFrame([features])
    probability = float(pipeline.predict_proba(frame)[:, 1][0])
    severity, action, approval_required = _decision(probability)
    observed_at = datetime.now(timezone.utc).isoformat()
    risk_score = round(probability * 100, 1)

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO risk_history (
                observed_at, device_id, source, model, risk_probability, risk_score,
                severity, recommended_action, human_approval_required,
                proxy_mismatch, dns_failure_rate, tls_error_count,
                adapter_reset_count, winhttp_drift, network_profile
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observed_at,
                payload.device_id,
                payload.source,
                payload.model,
                probability,
                risk_score,
                severity,
                action,
                int(approval_required),
                payload.proxy_mismatch,
                payload.dns_failure_rate,
                payload.tls_error_count,
                payload.adapter_reset_count,
                payload.winhttp_drift,
                payload.network_profile,
            ),
        )
        connection.commit()

    return {
        "observed_at": observed_at,
        "device_id": payload.device_id,
        "source": payload.source,
        "model": payload.model,
        "risk_probability": round(probability, 6),
        "risk_score": risk_score,
        "severity": severity,
        "recommended_action": action,
        "human_approval_required": approval_required,
        "governance_note": (
            "Model output is decision evidence, not an autonomous remediation command."
        ),
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "artifacts_present": ARTIFACTS.exists(),
        "metrics_present": (ARTIFACTS / "metrics.json").exists(),
        "frontend_present": (FRONTEND / "index.html").exists(),
        "history_database": str(HISTORY_DB.relative_to(ROOT)),
    }


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    return _load_metrics()


@app.get("/api/models")
def models() -> dict[str, Any]:
    available: list[str] = []
    if ARTIFACTS.exists():
        available = sorted(
            p.stem
            for p in ARTIFACTS.glob("*.joblib")
            if p.stem != "isolation_forest"
        )
    return {"models": available}


@app.post("/api/predict")
def predict(payload: PredictionRequest) -> dict[str, Any]:
    return _predict(payload)


@app.post("/api/telemetry")
def ingest_telemetry(payload: TelemetryRequest) -> dict[str, Any]:
    """Score a collector payload and persist it as live telemetry evidence."""
    prediction = PredictionRequest(**payload.model_dump(), source="telemetry")
    return _predict(prediction)


@app.get("/api/history")
def history(
    device_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    query = "SELECT * FROM risk_history"
    params: list[Any] = []
    if device_id:
        query += " WHERE device_id = ?"
        params.append(device_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _connect() as connection:
        rows = [dict(row) for row in connection.execute(query, params).fetchall()]

    for row in rows:
        row["human_approval_required"] = bool(row["human_approval_required"])
    rows.reverse()
    return {"count": len(rows), "items": rows}


@app.get("/api/explainability")
def explainability(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    """Return global SHAP importance exported by ml/explain_model.py."""
    path = ARTIFACTS / "shap_importance.csv"
    if not path.exists():
        return {
            "status": "not_generated",
            "message": (
                "Generate SHAP importance with ml/explain_model.py to populate this view."
            ),
            "features": [],
        }

    frame = pd.read_csv(path).head(limit)
    features = [
        {
            "feature": str(row["feature"]),
            "mean_abs_shap": float(row["mean_abs_shap"]),
        }
        for _, row in frame.iterrows()
    ]
    return {"status": "ready", "features": features}


@app.get("/api/drift")
def drift(device_id: str | None = None) -> dict[str, Any]:
    """Compare recent risk scores with the preceding baseline window.

    This is an operational drift indicator, not a formal statistical drift test.
    """
    with _connect() as connection:
        if device_id:
            rows = connection.execute(
                "SELECT risk_score FROM risk_history WHERE device_id = ? ORDER BY id DESC LIMIT 40",
                (device_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT risk_score FROM risk_history ORDER BY id DESC LIMIT 40"
            ).fetchall()

    scores = [float(row["risk_score"]) for row in reversed(rows)]
    if len(scores) < 10:
        return {
            "status": "insufficient_data",
            "sample_count": len(scores),
            "message": "At least 10 persisted predictions are required for the drift indicator.",
        }

    split = max(5, len(scores) // 2)
    baseline = scores[:-split]
    recent = scores[-split:]
    if not baseline:
        baseline = scores[:split]
        recent = scores[split:]

    baseline_mean = sum(baseline) / len(baseline)
    recent_mean = sum(recent) / len(recent)
    delta = recent_mean - baseline_mean
    return {
        "status": "ready",
        "sample_count": len(scores),
        "baseline_mean_risk": round(baseline_mean, 2),
        "recent_mean_risk": round(recent_mean, 2),
        "delta": round(delta, 2),
        "direction": "up" if delta > 2 else "down" if delta < -2 else "stable",
        "note": (
            "Heuristic risk-score drift indicator; add PSI/KS/feature drift for formal monitoring."
        ),
    }


# Mount the dashboard last so /api/* routes keep precedence.
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")

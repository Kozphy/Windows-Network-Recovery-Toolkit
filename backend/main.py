from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .auth import AuthUser, get_current_user
from .billing import create_checkout_session, verify_webhook
from .db import (
    ensure_user_org_project,
    get_history,
    get_project_for_user,
    get_recent_metrics,
    get_subscription,
    get_usage,
    init_db,
    increment_usage,
    insert_diagnosis,
    insert_metric,
    month_key,
    update_subscription,
)
from .engine import DiagnoseInput, classify_root_cause, detect_anomaly


class DiagnoseRequest(BaseModel):
    ping: bool
    dns: bool
    https: bool
    proxy: bool
    time_wait: int = Field(ge=0)
    established: int = Field(ge=0)
    project_id: Optional[str] = None


class DiagnoseResponse(BaseModel):
    root_cause: str
    confidence: str
    recommendation: str
    risk: str
    anomaly: Optional[dict] = None


class MonitorRequest(BaseModel):
    time_wait: int = Field(ge=0)
    established: int = Field(ge=0)
    project_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    org_id: str
    price_id: str
    success_url: str
    cancel_url: str


app = FastAPI(title="Windows Network Recovery Toolkit SaaS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


PLAN_LIMITS = {
    "free": 10,
    "pro": 500,
    "team": -1,  # unlimited
}


def _resolve_project(user: AuthUser, requested_project_id: Optional[str]) -> dict:
    ensure_user_org_project(user.user_id, user.email)
    project = get_project_for_user(user.user_id, requested_project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found for current user.")
    return project


def _enforce_usage_limit(org_id: str) -> dict:
    sub = get_subscription(org_id)
    usage = get_usage(org_id, month=month_key())
    plan = (sub.get("plan") or "free").lower()
    limit = PLAN_LIMITS.get(plan, 10)
    current = int(usage["diagnosis_count"])
    if limit != -1 and current >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Usage limit reached for plan '{plan}' ({limit}/month).",
        )
    return {"plan": plan, "limit": limit, "current": current}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(req: DiagnoseRequest, user: AuthUser = Depends(get_current_user)) -> dict:
    project = _resolve_project(user, req.project_id)
    org_id = project["org_id"]
    project_id = project["project_id"]

    _enforce_usage_limit(org_id)

    recent_metrics = get_recent_metrics(project_id=project_id, limit=10)
    anomaly = detect_anomaly(req.time_wait, req.established, recent_metrics)
    result = classify_root_cause(
        DiagnoseInput(
            ping=req.ping,
            dns=req.dns,
            https=req.https,
            proxy=req.proxy,
            time_wait=req.time_wait,
            established=req.established,
        ),
        anomaly,
    )
    result["anomaly"] = anomaly
    insert_diagnosis(project_id=project_id, input_data=req.model_dump(), result=result)
    insert_metric(project_id=project_id, time_wait=req.time_wait, established=req.established)
    current_count = increment_usage(org_id)
    sub = get_subscription(org_id)
    plan = (sub.get("plan") or "free").lower()
    limit = PLAN_LIMITS.get(plan, 10)
    result["usage"] = {
        "org_id": org_id,
        "plan": plan,
        "month": month_key(),
        "diagnosis_count": current_count,
        "limit": limit if limit != -1 else "unlimited",
    }
    return result


@app.post("/monitor")
def monitor(req: MonitorRequest, user: AuthUser = Depends(get_current_user)) -> dict:
    project = _resolve_project(user, req.project_id)
    project_id = project["project_id"]
    metric_id = insert_metric(project_id=project_id, time_wait=req.time_wait, established=req.established)
    recent_metrics = get_recent_metrics(project_id=project_id, limit=10)
    anomaly = detect_anomaly(req.time_wait, req.established, recent_metrics[1:])
    return {
        "id": metric_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stored": True,
        "anomaly": anomaly,
    }


@app.get("/history")
def history(
    limit: int = 100,
    project_id: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    project = _resolve_project(user, project_id)
    safe_limit = max(1, min(limit, 500))
    return get_history(org_id=project["org_id"], project_id=project_id, limit=safe_limit)


@app.get("/usage")
def usage(user: AuthUser = Depends(get_current_user), project_id: Optional[str] = None) -> dict:
    project = _resolve_project(user, project_id)
    org_id = project["org_id"]
    sub = get_subscription(org_id)
    u = get_usage(org_id, month=month_key())
    plan = (sub.get("plan") or "free").lower()
    limit = PLAN_LIMITS.get(plan, 10)
    remaining = "unlimited" if limit == -1 else max(0, limit - int(u["diagnosis_count"]))
    return {
        "org_id": org_id,
        "month": u["month"],
        "plan": plan,
        "status": sub.get("status", "active"),
        "diagnosis_count": int(u["diagnosis_count"]),
        "limit": limit if limit != -1 else "unlimited",
        "remaining": remaining,
    }


@app.post("/create-checkout-session")
def create_checkout(
    req: CheckoutRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    project = _resolve_project(user, None)
    if project["org_id"] != req.org_id:
        raise HTTPException(status_code=403, detail="Cannot create checkout for another organization.")

    session = create_checkout_session(
        customer_email=user.email,
        price_id=req.price_id,
        success_url=req.success_url,
        cancel_url=req.cancel_url,
        metadata={"org_id": req.org_id, "user_id": user.user_id},
    )
    return {"checkout_url": session.get("url"), "session_id": session.get("id")}


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = verify_webhook(payload, sig)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    event_type = event.get("type", "")
    data_object = (event.get("data") or {}).get("object") or {}
    metadata = data_object.get("metadata") or {}
    org_id = metadata.get("org_id")

    if org_id and event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "subscription_created",
        "subscription_updated",
        "subscription_canceled",
    }:
        status = data_object.get("status", "active")
        stripe_customer_id = data_object.get("customer")
        stripe_subscription_id = data_object.get("id")
        price_info = ((data_object.get("items") or {}).get("data") or [{}])[0]
        price_id = ((price_info.get("price") or {}).get("id")) or ""
        if "team" in price_id:
            plan = "team"
        elif "pro" in price_id:
            plan = "pro"
        else:
            plan = "free"
        if event_type in {"customer.subscription.deleted", "subscription_canceled"}:
            status = "canceled"
            plan = "free"
        update_subscription(
            org_id=org_id,
            plan=plan,
            status=status,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )

    return {"received": True, "type": event_type}

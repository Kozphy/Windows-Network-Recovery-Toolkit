"""FastAPI application for toolkit telemetry, diagnosis, and billing flows.

System placement:
    frontend/agent clients -> this API -> decision engine + SQLite persistence.

Key invariants:
    - User-scoped access is enforced through `get_current_user`.
    - Diagnosis requests are usage-metered by organization plan.
    - Billing webhook updates subscription state idempotently by org metadata.
"""

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
    insert_diagnosis,
    insert_metric,
    month_key,
    try_increment_usage_with_limit,
    update_subscription,
)
from .engine import DiagnoseInput, classify_root_cause, detect_anomaly


class DiagnoseRequest(BaseModel):
    """Input payload for rule-based diagnosis endpoint."""

    ping: bool
    dns: bool
    https: bool
    proxy: bool
    time_wait: int = Field(ge=0)
    established: int = Field(ge=0)
    project_id: Optional[str] = None


class DiagnoseResponse(BaseModel):
    """Output payload for diagnosis classification endpoint."""

    root_cause: str
    confidence: str
    recommendation: str
    risk: str
    anomaly: Optional[dict] = None


class MonitorRequest(BaseModel):
    """Input payload for connection trend monitoring endpoint."""

    time_wait: int = Field(ge=0)
    established: int = Field(ge=0)
    project_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    """Input payload for creating Stripe checkout sessions."""

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
    """Initialize backing database schema during app startup.

    Side effects:
        Executes schema DDL against local SQLite database.
    """
    init_db()


PLAN_LIMITS = {
    "free": 10,
    "pro": 500,
    "team": -1,  # unlimited
}


def _resolve_project(user: AuthUser, requested_project_id: Optional[str]) -> dict:
    """Resolve an accessible project for the authenticated user.

    Args:
        user: Current authenticated user context.
        requested_project_id: Optional project override from request.

    Returns:
        dict: Project row containing `org_id` and `project_id`.

    Raises:
        HTTPException: 404 when project is not accessible by current user.
    """
    ensure_user_org_project(user.user_id, user.email)
    project = get_project_for_user(user.user_id, requested_project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found for current user.")
    return project


def _get_plan_limit(org_id: str) -> dict:
    """Resolve plan name and monthly diagnosis limit for an organization."""
    sub = get_subscription(org_id)
    plan = (sub.get("plan") or "free").lower()
    limit = PLAN_LIMITS.get(plan, 10)
    return {"plan": plan, "limit": limit}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(req: DiagnoseRequest, user: AuthUser = Depends(get_current_user)) -> dict:
    """Run diagnosis workflow and persist resulting telemetry.

    Workflow:
        1) Resolve project scope and enforce plan usage limit.
        2) Detect anomaly from recent metric history.
        3) Classify root cause using deterministic rules.
        4) Persist diagnosis and metrics to SQLite.

    Side effects:
        - Increments usage counter for organization/month.
        - Writes diagnosis and metric rows to database.

    Idempotency:
        Not idempotent; each call increments usage and stores new records.

    Audit Notes:
        - What can go wrong: false positives from sparse history; over-limit
          rejection for heavy usage.
        - Detection: API 429 responses and stored diagnosis history.
        - Recovery: verify plan limits and rerun with updated telemetry.

    Args:
        req: Diagnosis signal payload.
        user: Authenticated user context (dependency-injected).

    Returns:
        dict: Classification result plus anomaly and usage metadata.

    Raises:
        HTTPException: 404 for missing project, 429 for plan limit exceeded.
    """
    project = _resolve_project(user, req.project_id)
    org_id = project["org_id"]
    project_id = project["project_id"]

    plan_info = _get_plan_limit(org_id)
    plan = plan_info["plan"]
    limit = plan_info["limit"]
    current_count = try_increment_usage_with_limit(org_id=org_id, limit=limit, month=month_key())
    if current_count is None:
        raise HTTPException(
            status_code=429,
            detail=f"Usage limit reached for plan '{plan}' ({limit}/month).",
        )

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
    """Persist connection counters and return anomaly assessment.

    Side effects:
        Writes one metric row to database.

    Idempotency:
        Not idempotent; repeated calls create additional metric rows.
    """
    project = _resolve_project(user, req.project_id)
    project_id = project["project_id"]
    recent_metrics = get_recent_metrics(project_id=project_id, limit=10)
    anomaly = detect_anomaly(req.time_wait, req.established, recent_metrics)
    metric_id = insert_metric(project_id=project_id, time_wait=req.time_wait, established=req.established)
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
    """Return bounded diagnosis/metrics history for current project scope."""
    project = _resolve_project(user, project_id)
    safe_limit = max(1, min(limit, 500))
    return get_history(org_id=project["org_id"], project_id=project_id, limit=safe_limit)


@app.get("/usage")
def usage(user: AuthUser = Depends(get_current_user), project_id: Optional[str] = None) -> dict:
    """Return current month usage and remaining diagnosis quota."""
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
    """Create Stripe checkout session for current user's organization.

    Side effects:
        Outbound API call to Stripe checkout endpoint.
    """
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
    """Validate Stripe webhook and synchronize subscription state.

    Side effects:
        - Verifies Stripe webhook signature.
        - Updates local subscription row when recognized billing events arrive.

    Idempotency:
        Best-effort idempotent for repeated webhook deliveries because updates
        overwrite current org subscription state.

    Audit Notes:
        - What can go wrong: invalid signature, missing org metadata, unknown
          event shape.
        - Detection: 400 invalid webhook responses and subscription mismatch.
        - Recovery: replay webhook after correcting secret/config metadata.
    """
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

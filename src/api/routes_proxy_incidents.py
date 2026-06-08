"""Proxy incident API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api import incident_store

router = APIRouter(prefix="/api/proxy", tags=["proxy-incidents"])


@router.get("/incidents")
def list_proxy_incidents(since_minutes: int = 1440) -> dict:
    return {"incidents": incident_store.list_incidents(since_minutes=since_minutes)}


@router.get("/incidents/{incident_id}")
def get_proxy_incident(incident_id: str) -> dict:
    bundle = incident_store.get_incident(incident_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return bundle


@router.get("/incidents/{incident_id}/timeline")
def get_incident_timeline(incident_id: str) -> dict:
    events = incident_store.get_timeline(incident_id)
    if not events:
        bundle = incident_store.get_incident(incident_id)
        if bundle is None:
            raise HTTPException(status_code=404, detail="incident not found")
    return {"incident_id": incident_id, "events": events}


@router.get("/incidents/{incident_id}/policy")
def get_incident_policy(incident_id: str) -> dict:
    bundle = incident_store.get_incident(incident_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return {"incident_id": incident_id, "policy": bundle.get("policy"), "classification": bundle.get("classification")}

"""Threat scenario models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ThreatScenario(BaseModel):
    threat_id: str
    name: str
    failure_mode: str
    description: str
    evidence_tier_required: str = "proof"


def threat_for_fixture(fixture: dict[str, Any]) -> ThreatScenario:
    override = fixture.get("threat")
    if override:
        return ThreatScenario.model_validate(override)
    classification = (fixture.get("classification") or {}).get("primary_classification", "")
    mapping = {
        "DEAD_PROXY_CONFIG": (
            "THREAT_DEAD_PROXY",
            "Dead localhost proxy breaks browser traffic",
            "WinINET references localhost proxy port with no active listener",
        ),
        "UNKNOWN_LOCAL_PROXY": (
            "THREAT_UNKNOWN_PROXY",
            "Unexplained local proxy listener",
            "Active localhost listener without confirmed registry writer",
        ),
        "POSSIBLE_MITM_RISK": (
            "THREAT_TLS_MISMATCH",
            "TLS path mismatch",
            "Direct vs proxied certificate chain divergence",
        ),
    }
    threat_id, name, failure_mode = mapping.get(
        classification,
        ("THREAT_PROXY_DRIFT", "Proxy configuration drift", "WinINET/WinHTTP or registry drift"),
    )
    return ThreatScenario(
        threat_id=threat_id,
        name=name,
        failure_mode=failure_mode,
        description=f"Derived from classification {classification or 'unknown'}",
    )

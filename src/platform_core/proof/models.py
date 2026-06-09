"""Proof outcome taxonomy — observation vs proof clearly separated."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProofOutcome(StrEnum):
    REMOTE_SERVER_FAILURE = "REMOTE_SERVER_FAILURE"
    LOCAL_PROXY_UPSTREAM_FAILURE = "LOCAL_PROXY_UPSTREAM_FAILURE"
    DNS_FAILURE = "DNS_FAILURE"
    TCP_CONNECT_FAILURE = "TCP_CONNECT_FAILURE"
    TLS_OR_HTTP_FAILURE = "TLS_OR_HTTP_FAILURE"
    DEAD_LOCALHOST_PROXY = "DEAD_LOCALHOST_PROXY"
    UNKNOWN_INCONCLUSIVE = "UNKNOWN_INCONCLUSIVE"


class ProofObservation(BaseModel):
    """Single probe observation — not a causal conclusion."""

    probe_id: str
    probe_type: str
    observed_value: str
    success: bool
    raw_excerpt: str = ""
    limitations: list[str] = Field(default_factory=list)


class ProofResult(BaseModel):
    """Proof engine output — separates observations from classified outcome."""

    proof_id: str
    timestamp_utc: str
    target_url: str
    observations: list[ProofObservation] = Field(default_factory=list)
    outcome: ProofOutcome = ProofOutcome.UNKNOWN_INCONCLUSIVE
    outcome_rationale: str = ""
    confidence_level: str = "medium"
    limitations: list[str] = Field(default_factory=list)
    is_proof: bool = False

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

"""TLS / MITM evidence models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MitmRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TlsCertificateSnapshot(BaseModel):
    path: str  # direct | proxied
    subject: str = ""
    issuer: str = ""
    san: list[str] = Field(default_factory=list)
    not_before: str = ""
    not_after: str = ""
    serial_number: str = ""
    fingerprint_sha256: str = ""
    chain: list[str] = Field(default_factory=list)
    raw_error: str = ""


class RootCaObservation(BaseModel):
    subject: str = ""
    issuer: str = ""
    thumbprint: str = ""
    not_before: str = ""
    not_after: str = ""
    store: str = ""
    suspicious: bool = False
    suspicion_reason: str = ""


class TlsProofResult(BaseModel):
    proof_id: str
    timestamp_utc: str
    target_url: str
    direct_cert: TlsCertificateSnapshot
    proxied_cert: TlsCertificateSnapshot | None = None
    certificate_mismatch: bool = False
    mismatch_fields: list[str] = Field(default_factory=list)
    mitm_risk_level: MitmRiskLevel = MitmRiskLevel.LOW
    root_ca_observations: list[RootCaObservation] = Field(default_factory=list)
    suspicious_roots: list[RootCaObservation] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

"""URL diagnostic data models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProbeStatus(StrEnum):
    OK = "OK"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class ClassificationPrimary(StrEnum):
    DNS_FAILURE = "DNS_FAILURE"
    TCP_CONNECT_FAILURE = "TCP_CONNECT_FAILURE"
    PROXY_FAILURE = "PROXY_FAILURE"
    TLS_FAILURE = "TLS_FAILURE"
    REMOTE_SERVER_ERROR = "REMOTE_SERVER_ERROR"
    APPLICATION_RESOURCE_NOT_FOUND = "APPLICATION_RESOURCE_NOT_FOUND"
    PERMISSION_OR_ACCESS_DENIED = "PERMISSION_OR_ACCESS_DENIED"
    SOFT_404_OR_CONTENT_NOT_FOUND = "SOFT_404_OR_CONTENT_NOT_FOUND"
    REDIRECT_LOOP_OR_CHAIN_FAILURE = "REDIRECT_LOOP_OR_CHAIN_FAILURE"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    TRACKING_SHORTLINK_ISSUE = "TRACKING_SHORTLINK_ISSUE"
    REGIONAL_ACCOUNT_VISIBILITY = "REGIONAL_ACCOUNT_VISIBILITY"
    UNKNOWN_APPLICATION_LAYER_FAILURE = "UNKNOWN_APPLICATION_LAYER_FAILURE"


class ClassificationSecondary(StrEnum):
    LINKEDIN_SOFT_404 = "LINKEDIN_SOFT_404"
    REDIRECT_DOMAIN_CHANGE = "REDIRECT_DOMAIN_CHANGE"
    LOGIN_WALL = "LOGIN_WALL"
    SHORTLINK_EXPANDED = "SHORTLINK_EXPANDED"


class UrlDiagnosticInput(BaseModel):
    url: str
    domain_profile: str = "generic"
    follow_redirects: bool = True
    max_redirects: int = 10
    compare_browser: bool = False
    user_agent: str = ""
    timeout: float = 10.0
    no_body: bool = False
    classify_soft_404: bool = True
    save_evidence: bool = False
    evidence_dir: str = "./evidence"


class DnsObservation(BaseModel):
    status: ProbeStatus = ProbeStatus.SKIPPED
    resolved_ips: list[str] = Field(default_factory=list)
    error: str = ""


class TcpObservation(BaseModel):
    status: ProbeStatus = ProbeStatus.SKIPPED
    remote_host: str = ""
    remote_port: int = 443
    error: str = ""


class TlsObservation(BaseModel):
    status: ProbeStatus = ProbeStatus.SKIPPED
    issuer: str = ""
    subject: str = ""
    sni: str = ""
    error: str = ""


class RedirectHop(BaseModel):
    url: str
    status_code: int | None = None


class HttpObservation(BaseModel):
    status: ProbeStatus = ProbeStatus.SKIPPED
    status_code: int | None = None
    final_url: str = ""
    redirect_chain: list[str] = Field(default_factory=list)
    redirect_hops: list[RedirectHop] = Field(default_factory=list)
    content_type: str = ""
    title: str = ""
    body_fingerprint: str = ""
    body_length: int = 0
    soft_404_signals: list[str] = Field(default_factory=list)
    login_signals: list[str] = Field(default_factory=list)
    error: str = ""
    proxy_error: bool = False


class RedirectObservation(BaseModel):
    hop_count: int = 0
    loop_detected: bool = False
    domain_changed: bool = False
    original_domain: str = ""
    final_domain: str = ""
    suspicious_shortlink: bool = False
    expanded_url: str = ""


class Soft404Observation(BaseModel):
    detected: bool = False
    signals: list[str] = Field(default_factory=list)
    profile: str = "generic"


class BrowserCompareObservation(BaseModel):
    wininet_proxy_enabled: bool = False
    wininet_proxy_server: str = ""
    winhttp_direct_access: bool = True
    env_http_proxy: str = ""
    env_https_proxy: str = ""
    request_succeeded: bool = False
    browser_ua_succeeded: bool | None = None
    mismatches: list[str] = Field(default_factory=list)


class UrlDiagnosticClassification(BaseModel):
    primary: ClassificationPrimary
    secondary: list[str] = Field(default_factory=list)
    network_reachable: bool = False
    resource_reachable: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class RiskAssessmentBlock(BaseModel):
    severity: str = "LOW"
    user_impact: str = ""
    not_evidence_of: list[str] = Field(default_factory=list)


class DecisionBlock(BaseModel):
    safe_to_auto_fix_network: bool = False
    reason: str = ""


class AuditBlock(BaseModel):
    evidence_files: list[str] = Field(default_factory=list)


class UrlDiagnosticReport(BaseModel):
    schema_version: str = "1.0"
    command: str = "url-diagnose"
    input: UrlDiagnosticInput
    observations: dict[str, Any] = Field(default_factory=dict)
    classification: UrlDiagnosticClassification
    risk_assessment: RiskAssessmentBlock
    recommended_next_steps: list[str] = Field(default_factory=list)
    decision: DecisionBlock
    audit: AuditBlock = Field(default_factory=AuditBlock)
    limitations: list[str] = Field(default_factory=list)
    browser_compare: BrowserCompareObservation | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

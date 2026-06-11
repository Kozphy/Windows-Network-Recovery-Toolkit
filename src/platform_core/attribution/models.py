"""Proxy listener and registry attribution models — diagnostic only."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ListenerClassification(StrEnum):
    NO_PROXY = "NO_PROXY"
    KNOWN_DEV_PROXY = "KNOWN_DEV_PROXY"
    KNOWN_SECURITY_TOOL = "KNOWN_SECURITY_TOOL"
    KNOWN_VPN_PROXY = "KNOWN_VPN_PROXY"
    UNKNOWN_LOCAL_PROXY = "UNKNOWN_LOCAL_PROXY"
    SUSPICIOUS_PROXY = "SUSPICIOUS_PROXY"
    POSSIBLE_MITM_RISK = "POSSIBLE_MITM_RISK"
    DEAD_PROXY_CONFIG = "DEAD_PROXY_CONFIG"


class ProcessAttribution(BaseModel):
    pid: int | None = None
    parent_pid: int | None = None
    executable_path: str = ""
    command_line: str = ""
    process_name: str = ""
    start_time_utc: str = ""
    publisher: str = ""
    signature_status: str = ""
    user_session: str = ""


class ProxyStateSnapshot(BaseModel):
    wininet_proxy_enable: int = 0
    wininet_proxy_server: str = ""
    wininet_proxy_override: str = ""
    wininet_auto_config_url: str = ""
    winhttp_raw: str = ""
    winhttp_direct_access: bool = True
    localhost_port: int | None = None


class AttributionSnapshot(BaseModel):
    """Read-only proxy/registry/process attribution — no mutations."""

    snapshot_id: str
    timestamp_utc: str
    proxy_state: ProxyStateSnapshot
    listener: ProcessAttribution = Field(default_factory=ProcessAttribution)
    classification: ListenerClassification = ListenerClassification.NO_PROXY
    classification_rationale: str = ""
    limitations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

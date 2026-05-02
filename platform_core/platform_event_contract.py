"""Interview-ready canonical event envelopes for the Endpoint Reliability Platform.

These Pydantic models describe **logical** JSONL/API shapes layered on append-only stores in
``platform_data/``. They complement :mod:`platform_core.models` (operational primitives) and
:mod:`platform_core.events` (normalized replay envelopes).

Timezone:
    ``timestamp_utc`` fields MUST be RFC3339 UTC ISO strings (use :func:`platform_core.models.utc_now_iso`).

Schema versioning:
    ``schema_version`` defaults to ``"1"`` — bump deliberately when migrating consumers.

See Also:
    ``docs/architecture_platform.md`` for diagram context.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from platform_core.models import utc_now_iso


class PlatformEventEnvelope(BaseModel):
    """Minimal envelope shared by distinct platform semantic events."""

    schema_version: str = "1"
    event_id: str
    timestamp_utc: str = Field(default_factory=utc_now_iso)
    endpoint_id: str = ""
    event_type: str = "platform.event"
    payload: dict[str, Any] = Field(default_factory=dict)


class EndpointHeartbeat(PlatformEventEnvelope):
    """Agent or CLI heartbeat — registers liveness without diagnostic payload."""

    event_type: Literal["endpoint.heartbeat"] = "endpoint.heartbeat"
    endpoint_id: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Typically os_family, os_version, agent_version mirrors.",
    )


class NetworkStateSnapshot(PlatformEventEnvelope):
    """Privacy-scrubbed network / proxy snapshot row (mirror of EndpointSnapshot semantics)."""

    event_type: Literal["network.snapshot"] = "network.snapshot"
    endpoint_id: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="network_state, proxy_state, dns_state, tcp_state blobs — redacted upstream.",
    )


class ProxyDriftEvent(PlatformEventEnvelope):
    """WinINET-aligned drift marker between consecutive polls or diff engines."""

    event_type: Literal["proxy.drift"] = "proxy.drift"
    endpoint_id: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="changed_fields, risk_level, parsed_proxy fragments when present.",
    )


class EvidenceEvent(PlatformEventEnvelope):
    """Normalized evidence ingest (Sysmon-shaped row, Procmon CSV excerpt, ETW stub, etc.)."""

    event_type: Literal["evidence.row"] = "evidence.row"
    endpoint_id: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="evidence_subtype, attribution_level_hint, sanitized excerpt refs.",
    )


class PlatformAttributionResult(PlatformEventEnvelope):
    """Fused attribution verdict serialized for ``GET /platform/attribution/{event_id}``.

    Note:
        Mirrors :class:`evidence.models.AttributionResult` dict layout inside ``payload`` for strict typing
        helpers while keeping envelope correlation keys top-level.
    """

    event_type: Literal["attribution.result"] = "attribution.result"
    endpoint_id: str = ""
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="candidate_actor, confidence, attribution_level, evidence[], notes.",
    )


class PlatformPolicyDecision(PlatformEventEnvelope):
    """Serialized policy router outcome (distinct from remediation preview rows)."""

    event_type: Literal["policy.decision"] = "policy.decision"
    endpoint_id: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="decision verb, reason_codes[], risk tier, remediation_action key hints.",
    )


class RemediationPreviewEvent(PlatformEventEnvelope):
    """Preview artifact correlation — ``preview_id`` lives in payload or dedicated field."""

    event_type: Literal["remediation.preview"] = "remediation.preview"
    endpoint_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RemediationExecutionEvent(PlatformEventEnvelope):
    """Execution outcome envelope mirroring ``RemediationExecution.execution_id``."""

    event_type: Literal["remediation.execution"] = "remediation.execution"
    endpoint_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditPlatformEvent(PlatformEventEnvelope):
    """Operator/system audit lineage for dashboard explorers."""

    event_type: Literal["audit.platform"] = "audit.platform"
    endpoint_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class IncidentClusterPayload(BaseModel):
    """Summarized cluster emitted by KPI surfaces (distinct UUID from IncidentCluster internals OK)."""

    cluster_id: str
    category: str
    pattern_key: str = ""
    event_ids: list[str] = Field(default_factory=list)
    endpoint_ids: list[str] = Field(default_factory=list)
    first_seen_at: str = ""
    last_seen_at: str = ""
    cluster_severity: str = "low"
    affected_endpoint_count: int = 0
    event_count: int = 0


class IncidentClusterEvent(PlatformEventEnvelope):
    """Cluster snapshot row for timelines / dashboards."""

    event_type: Literal["incident.cluster"] = "incident.cluster"
    endpoint_id: str = "*"  # multi-endpoint sentinel when not singleton-scoped
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_cluster_payload(cls, c: IncidentClusterPayload) -> IncidentClusterEvent:
        return cls(
            event_id=str(c.cluster_id),
            endpoint_id="*",
            payload=c.model_dump(),
        )

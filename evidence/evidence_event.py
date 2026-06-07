"""Normalized evidence record for ingestion prior to attribution correlation.

Module responsibility:
    Provide a stdlib :class:`~dataclasses.dataclass` transport for **single** evidence observations (Procmon row,
    Sysmon dict excerpt, ETW stub fragment) before fusion via :func:`~evidence.attribution_engine.build_attribution`.

System placement:
    Parallel to :class:`platform_core.platform_event_contract.EvidenceEvent` Pydantic envelope—this dataclass stays
    lightweight for collectors/tests without importing ``pydantic``.

Key invariants:
    * ``payload`` is caller-defined JSON-compatible leaves—must **exclude** secrets unless redacted upstream.
    * ``evidence_type`` categorizes provenance for dashboards—not localized UI copy.

Timezone:
    ``timestamp_utc`` must follow RFC3339 UTC conventions consistent with :func:`platform_core.models.utc_now_iso`.

Output guarantees:
    :meth:`EvidenceEvent.as_dict` returns plain dicts suitable for JSON serialization tests.

Side effects:
    None at rest—serializers allocate dict copies only.

Audit Notes:
    Rows labeled ``procmon_csv`` / ``sysmon_eid13`` still require trusted exporters—treat as tamper-susceptible unless
    paired with tamper-evident logging elsewhere (see ``docs/evidence_pipeline.md``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EvidenceSubtype = Literal[
    "procmon_csv", "sysmon_eid13", "etw_stub", "registry_poll", "listener_hint", "other"
]


@dataclass
class EvidenceEvent:
    """Single correlated evidence datum prior to fused :class:`~evidence.models.AttributionResult`.

    Attributes:
        event_id: Stable correlation token within the ingestion batch.
        timestamp_utc: RFC3339 UTC instant string recorded by collector or fixture author.
        endpoint_id: Privacy-preserving endpoint identifier matching platform ingestion conventions.
        schema_version: Dataclass schema revision—default ``"1"``.
        evidence_type: Provenance tag—extend strings cautiously to avoid dashboard drift.
        payload: Structured excerpt (paths, operation names, hashes) already sanitized when sensitive.

    Raises:
        ``dataclass`` init raises ``TypeError`` on incompatible assignments during construction only.
    """

    event_id: str
    timestamp_utc: str
    endpoint_id: str
    schema_version: str = "1"
    evidence_type: EvidenceSubtype | str = "other"
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialize to JSON-friendly mapping using :func:`dataclasses.asdict`.

        Returns:
            Shallow dict copy—nested dicts inside ``payload`` alias mutable structures unless deep-copied by caller.

        Side effects:
            Allocates new dict/list structures via ``asdict``.
        """

        return asdict(self)

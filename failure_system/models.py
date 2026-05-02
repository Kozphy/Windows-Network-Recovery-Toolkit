"""Pydantic models for the Failure Knowledge System (`failure_system`).

This package turns normalized diagnostic snapshots into typed ``FailureBlock`` records for
local JSONL storage, HTTP APIs, and CLI search.

System placement:
    ``collector`` produces ``DiagnosticSnapshot`` → ``rules.RuleEngine`` emits
    ``RuleOutcome`` rows → ``generator.build_failure_block`` materializes ``FailureBlock`` →
    ``storage`` appends JSON lines under ``data/failure_blocks/``.

Key invariants:
    - ``FailureBlock.created_at`` is populated in UTC by ``generator.build_failure_block``.
    - ``confidence_score`` clamps to ``[0.0, 1.0]`` via ``FailureBlock`` field validator.
    - ``diagnostic_commands`` embeds truncated command stdout for audit/search (not structured metrics).

Timezone:
    Datetimes written by this package use timezone-aware UTC.

Failure modes:
    Malformed JSONL rows fail ``FailureBlock.model_validate`` at read time—inspect or delete the
    offending shard line before retrying search APIs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    """Human-facing repair severity tier for recommended manual actions.

    Values classify narrative guidance bundled into ``FailureBlock`` records; they do not
    execute repairs automatically.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DiagnosticCommandResult(BaseModel):
    """Single command outcome from the safe diagnostic collector."""

    command: list[str] = Field(description="Argv-style command list (no shell).")
    exit_code: int
    stdout: str = Field(default="", description="Merged stdout/stderr, truncated by collector.")
    ok: bool = Field(description="Semantic success for this probe (not always exit_code==0).")


class DiagnosticSnapshot(BaseModel):
    """Normalized snapshot derived from raw diagnostic commands."""

    ping_ip_ok: bool = Field(description="ICMP to a well-known public IP succeeded.")
    nslookup_ok: bool = Field(description="DNS resolution for a test name succeeded.")
    curl_https_ok: bool = Field(description="HTTPS fetch to a stable test URL succeeded.")
    winhttp_direct: bool = Field(
        default=True,
        description="WinHTTP reports direct access (no proxy server line active).",
    )
    proxy_server_line_present: bool = Field(
        default=False,
        description="WinHTTP output suggests an explicit proxy server is configured.",
    )
    intermittent_reported: bool = Field(
        default=False,
        description="Operator flagged intermittent failures (multi-run / historical context).",
    )
    raw: dict[str, DiagnosticCommandResult] = Field(
        default_factory=dict,
        description="Raw command results keyed by probe name.",
    )


class RuleOutcome(BaseModel):
    """One fired rule from the deterministic rule engine."""

    rule_id: str
    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    recommended_next_action: str


class FailureBlock(BaseModel):
    """Immutable-style knowledge record summarizing one diagnostic pass.

    Attributes:
        id: Unique identifier for deduplication in APIs (UUIDv4 from generator).
        diagnostic_commands: Map of probe key to concatenated stdout/stderr text (truncated upstream).
        source_logs: Compact provenance strings (rule ids, clipped explanations)—not raw machine logs.

    Audit Notes:
        Treat ``diagnostic_commands`` as potentially sensitive host output; redact before sharing
        outside the operator workstation.
    """

    id: UUID
    name: str = Field(min_length=1, max_length=256)
    symptom: str
    observed_signals: list[str] = Field(default_factory=list)
    likely_causes: list[str] = Field(default_factory=list)
    diagnostic_commands: dict[str, str] = Field(
        default_factory=dict,
        description="Probe name → truncated stdout for audit/search.",
    )
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommended_fix: str
    risk_level: RiskLevel
    safety_boundary: str = Field(
        description="What this system will not do automatically; scope limits.",
    )
    rollback_plan: str = Field(description="How to undo or mitigate the suggested change.")
    created_at: datetime
    source_logs: list[str] = Field(
        default_factory=list,
        description="Sanitized snippets or references; never raw secrets.",
    )

    @field_validator("confidence_score")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        """Clamp model confidence into ``[0.0, 1.0]`` for stable sorting."""

        return max(0.0, min(1.0, v))


class FailureBlockSummary(BaseModel):
    """Lightweight listing shape for APIs."""

    id: UUID
    name: str
    symptom: str
    confidence_score: float
    risk_level: RiskLevel
    created_at: datetime


class FixRecommendation(BaseModel):
    """Repair guidance without executing repairs."""

    failure_block_id: UUID | None = None
    title: str
    rationale: str
    recommended_fix: str
    risk_level: RiskLevel
    rollback_plan: str
    safety_notes: str
    requires_explicit_confirmation: bool = True


class DiagnoseRequest(BaseModel):
    """Optional flags for POST /diagnose."""

    intermittent: bool = False


class RecommendFixRequest(BaseModel):
    """Lookup failure knowledge for safe textual recommendation."""

    failure_block_id: UUID | None = None
    query: str | None = Field(default=None, description="Search symptom/causes when id omitted.")

    model_config = {"extra": "forbid"}


class DiagnoseResponse(BaseModel):
    failure_block: FailureBlock
    rule_outcomes: list[RuleOutcome]
    stored_path: str | None = None
    explanation_text: str = Field(
        default="",
        description="Plain-English 2–3 sentence summary for UI or reports (no repairs executed).",
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


def failure_block_to_summary(block: FailureBlock) -> FailureBlockSummary:
    """Project a ``FailureBlock`` into a lightweight API listing row.

    Args:
        block: Fully populated failure knowledge record.

    Returns:
        ``FailureBlockSummary`` omitting diagnostic payloads and narrative fields.
    """
    return FailureBlockSummary(
        id=block.id,
        name=block.name,
        symptom=block.symptom,
        confidence_score=block.confidence_score,
        risk_level=block.risk_level,
        created_at=block.created_at,
    )

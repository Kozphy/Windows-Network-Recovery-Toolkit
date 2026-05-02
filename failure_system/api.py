"""FastAPI surface for the Failure Knowledge System.

System placement:
    Optional HTTP adapter layered on top of ``collector``, ``rules``, ``generator``, ``storage``,
    and ``search``—mirrors ``python -m failure_system`` semantics without executing repairs.

Environment variables:
    ``FAILURE_SYSTEM_DATA_DIR`` overrides the JSONL root (same variable as the CLI).

Audit Notes:
    ``POST /diagnose`` mutates disk via ``append_failure_block``; monitor shard growth on shared hosts.

Failure modes:
    ``POST /recommend-fix`` raises HTTP 404 when identifiers/queries miss persisted data; malformed
    JSON bodies surface FastAPI validation errors before handlers run.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Body, FastAPI, HTTPException, Query
from failure_system import __version__
from failure_system.collector import collect_diagnostics
from failure_system.generator import build_failure_block
from failure_system.models import (
    DiagnoseRequest,
    DiagnoseResponse,
    FailureBlock,
    FailureBlockSummary,
    HealthResponse,
    RecommendFixRequest,
    failure_block_to_summary,
)
from failure_system.recommend import recommend_by_id, recommend_by_query
from failure_system.rules import RuleEngine
from failure_system.storage import append_failure_block, default_data_dir, iter_failure_blocks


def resolve_data_dir() -> Path:
    """Return JSONL directory from ``FAILURE_SYSTEM_DATA_DIR`` or package default."""

    env = os.environ.get("FAILURE_SYSTEM_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return default_data_dir()


def create_app() -> FastAPI:
    """Construct FastAPI app wiring diagnose/search/recommend routes."""

    app = FastAPI(
        title="Failure Knowledge System",
        version=__version__,
        description="Structured FailureBlocks from safe Windows network diagnostics (no auto-repair).",
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @app.post("/diagnose", response_model=DiagnoseResponse)
    def diagnose(body: DiagnoseRequest | None = Body(default=None)) -> DiagnoseResponse:
        req = body or DiagnoseRequest()
        snapshot = collect_diagnostics(intermittent_reported=req.intermittent)
        engine = RuleEngine()
        outcomes = engine.evaluate(snapshot)
        block = build_failure_block(snapshot, outcomes)
        data_dir = resolve_data_dir()
        written = append_failure_block(block, data_dir=data_dir)
        return DiagnoseResponse(
            failure_block=block,
            rule_outcomes=outcomes,
            stored_path=str(written),
        )

    @app.get("/failure-blocks", response_model=list[FailureBlockSummary])
    def list_failure_blocks(limit: int = Query(default=100, ge=1, le=500)) -> list[FailureBlockSummary]:
        data_dir = resolve_data_dir()
        blocks = list(iter_failure_blocks(data_dir))
        blocks.sort(key=lambda b: b.created_at, reverse=True)
        return [failure_block_to_summary(b) for b in blocks[:limit]]

    @app.get("/failure-blocks/search", response_model=list[FailureBlock])
    def search_blocks(
        q: Annotated[str, Query(min_length=1)],
        limit: int = Query(default=25, ge=1, le=200),
    ) -> list[FailureBlock]:
        from failure_system.search import search_failure_blocks

        data_dir = resolve_data_dir()
        return search_failure_blocks(q, data_dir=data_dir, limit=limit)

    @app.post("/recommend-fix")
    def recommend_fix(body: RecommendFixRequest) -> dict[str, object]:
        data_dir = resolve_data_dir()
        if body.failure_block_id is not None:
            rec = recommend_by_id(body.failure_block_id, data_dir=data_dir)
            if rec is None:
                raise HTTPException(status_code=404, detail="failure_block_id not found")
            return {"recommendation": rec.model_dump(mode="json")}
        if body.query:
            rec = recommend_by_query(body.query, data_dir=data_dir)
            if rec is None:
                raise HTTPException(status_code=404, detail="no matching FailureBlock for query")
            return {"recommendation": rec.model_dump(mode="json")}
        raise HTTPException(
            status_code=400,
            detail="Provide failure_block_id or query",
        )

    return app


app = create_app()

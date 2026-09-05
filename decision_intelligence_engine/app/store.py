from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, create_engine, select
from sqlalchemy.engine import Engine

from .models import HumanDecisionResult, OutcomeResult, Recommendation

metadata = MetaData()

decisions = Table(
    "decisions",
    metadata,
    Column("decision_id", String(64), primary_key=True),
    Column("requester", String(255), nullable=False),
    Column("status", String(64), nullable=False),
    Column("recommendation_json", Text, nullable=False),
    Column("human_decision_json", Text, nullable=True),
    Column("outcome_json", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class DecisionStore:
    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or os.getenv("DI_DATABASE_URL", "sqlite:///data/decisions.db")
        if url.startswith("sqlite:///"):
            db_path = Path(url.removeprefix("sqlite:///"))
            if db_path.parent != Path("."):
                db_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, future=True, connect_args=connect_args)
        metadata.create_all(self.engine)

    def save_recommendation(self, recommendation: Recommendation) -> None:
        now = datetime.now(timezone.utc)
        payload = recommendation.model_dump_json()
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(decisions.c.decision_id).where(decisions.c.decision_id == recommendation.decision_id)
            ).first()
            if existing:
                conn.execute(
                    decisions.update()
                    .where(decisions.c.decision_id == recommendation.decision_id)
                    .values(recommendation_json=payload, status=recommendation.status, updated_at=now)
                )
            else:
                conn.execute(
                    decisions.insert().values(
                        decision_id=recommendation.decision_id,
                        requester=recommendation.requester,
                        status=recommendation.status,
                        recommendation_json=payload,
                        human_decision_json=None,
                        outcome_json=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def get_recommendation(self, decision_id: str) -> Recommendation | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(decisions.c.recommendation_json).where(decisions.c.decision_id == decision_id)
            ).first()
        return Recommendation.model_validate_json(row[0]) if row else None

    def get_status(self, decision_id: str) -> str | None:
        with self.engine.begin() as conn:
            row = conn.execute(select(decisions.c.status).where(decisions.c.decision_id == decision_id)).first()
        return row[0] if row else None

    def save_human_decision(self, result: HumanDecisionResult) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                decisions.update()
                .where(decisions.c.decision_id == result.decision_id)
                .values(
                    status=result.status,
                    human_decision_json=result.model_dump_json(),
                    updated_at=datetime.now(timezone.utc),
                )
            )

    def get_human_decision(self, decision_id: str) -> HumanDecisionResult | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(decisions.c.human_decision_json).where(decisions.c.decision_id == decision_id)
            ).first()
        if not row or not row[0]:
            return None
        return HumanDecisionResult.model_validate(json.loads(row[0]))

    def save_outcome(self, result: OutcomeResult) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                decisions.update()
                .where(decisions.c.decision_id == result.decision_id)
                .values(
                    outcome_json=result.model_dump_json(),
                    updated_at=datetime.now(timezone.utc),
                )
            )

    def get_outcome(self, decision_id: str) -> OutcomeResult | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(decisions.c.outcome_json).where(decisions.c.decision_id == decision_id)
            ).first()
        if not row or not row[0]:
            return None
        return OutcomeResult.model_validate(json.loads(row[0]))

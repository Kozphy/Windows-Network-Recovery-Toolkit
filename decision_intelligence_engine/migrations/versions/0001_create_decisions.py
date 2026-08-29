from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_create_decisions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("decision_id", sa.String(length=64), primary_key=True),
        sa.Column("requester", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("recommendation_json", sa.Text(), nullable=False),
        sa.Column("human_decision_json", sa.Text(), nullable=True),
        sa.Column("outcome_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("decisions")

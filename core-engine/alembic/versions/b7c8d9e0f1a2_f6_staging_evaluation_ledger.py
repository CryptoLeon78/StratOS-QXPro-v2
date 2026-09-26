"""add immutable F6 staging evaluation ledger

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "f6_staging_evaluation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("pipeline_candidate.id"), nullable=False),
        sa.Column("evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("configuration_sha256", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("requested_sizing_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("gates", postgresql.JSONB(), nullable=False),
        sa.Column("challenger", postgresql.JSONB(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id", "evidence_sha256"),
    )
    op.create_index(
        "ix_f6_staging_evaluation_candidate_at",
        "f6_staging_evaluation",
        ["candidate_id", "evaluated_at"],
    )
    op.execute("REVOKE UPDATE, DELETE ON f6_staging_evaluation FROM stratos_app")


def downgrade() -> None:
    op.drop_index("ix_f6_staging_evaluation_candidate_at", table_name="f6_staging_evaluation")
    op.drop_table("f6_staging_evaluation")

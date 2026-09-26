"""add immutable F6 evaluation ledger

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "f6_evaluation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("pipeline_candidate.id"), nullable=False),
        sa.Column("evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("configuration_sha256", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("gates", postgresql.JSONB(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id", "evidence_sha256"),
    )
    op.create_index("ix_f6_evaluation_candidate_at", "f6_evaluation", ["candidate_id", "evaluated_at"])
    op.execute("REVOKE UPDATE, DELETE ON f6_evaluation FROM stratos_app")


def downgrade() -> None:
    op.drop_index("ix_f6_evaluation_candidate_at", table_name="f6_evaluation")
    op.drop_table("f6_evaluation")

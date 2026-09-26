"""add source-scoped immutable correlation snapshots

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    correlation_source = postgresql.ENUM(
        "MT5_BACKTEST", "MT5_REAL", name="correlation_source", create_type=False
    )
    correlation_source.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "correlation_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", correlation_source, nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(), nullable=False),
        sa.Column("account_scope", postgresql.JSONB(), nullable=False),
        sa.Column("input_manifest", postgresql.JSONB(), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("source", "input_sha256"),
    )
    op.create_index("ix_correlation_snapshot_source_created", "correlation_snapshot", ["source", "created_at"])
    op.create_table(
        "correlation_snapshot_pair",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("correlation_snapshot.id"), nullable=False),
        sa.Column("bot_a_id", sa.Integer(), sa.ForeignKey("bot.id"), nullable=False),
        sa.Column("bot_b_id", sa.Integer(), sa.ForeignKey("bot.id"), nullable=False),
        sa.Column("correlation", sa.Float(), nullable=False),
        sa.Column("is_redundant_pair", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("snapshot_id", "bot_a_id", "bot_b_id"),
    )
    op.create_index("ix_correlation_snapshot_pair_snapshot", "correlation_snapshot_pair", ["snapshot_id"])
    op.execute("REVOKE UPDATE, DELETE ON correlation_snapshot FROM stratos_app")
    op.execute("REVOKE UPDATE, DELETE ON correlation_snapshot_pair FROM stratos_app")


def downgrade() -> None:
    op.drop_index("ix_correlation_snapshot_pair_snapshot", table_name="correlation_snapshot_pair")
    op.drop_table("correlation_snapshot_pair")
    op.drop_index("ix_correlation_snapshot_source_created", table_name="correlation_snapshot")
    op.drop_table("correlation_snapshot")
    postgresql.ENUM(name="correlation_source").drop(op.get_bind(), checkfirst=True)

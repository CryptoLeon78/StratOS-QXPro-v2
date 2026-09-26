"""add pipeline orchestrator work and agent command ledgers

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_work_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("source_key", sa.String(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "source_key"),
    )
    op.create_table(
        "pipeline_agent_command",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("pipeline_work_item.id"), nullable=True),
        sa.Column("command_type", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False, unique=True),
        sa.Column("request_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "pipeline_agent_command_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("command_id", sa.Integer(), sa.ForeignKey("pipeline_agent_command.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("REVOKE UPDATE, DELETE ON pipeline_agent_command FROM stratos_app")
    op.execute("REVOKE UPDATE, DELETE ON pipeline_agent_command_event FROM stratos_app")


def downgrade() -> None:
    op.drop_table("pipeline_agent_command_event")
    op.drop_table("pipeline_agent_command")
    op.drop_table("pipeline_work_item")

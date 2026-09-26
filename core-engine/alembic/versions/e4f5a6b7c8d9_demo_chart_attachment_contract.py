"""add immutable demo chart attachment contract

Revision ID: e4f5a6b7c8d9
Revises: d4e5f6a7b8c9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_chart_attachment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id", sa.Integer(), sa.ForeignKey("pipeline_candidate.id"), nullable=False
        ),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("operational_asset.id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("artifact_id", sa.Integer(), sa.ForeignKey("import_artifact.id"), nullable=False),
        sa.Column("magic_number", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("timeframe", sa.String(), nullable=False),
        sa.Column("ea_version", sa.String(), nullable=False),
        sa.Column("mql5_sha256", sa.String(length=64), nullable=False),
        sa.Column("compiled_ex5_sha256", sa.String(length=64), nullable=False),
        sa.Column("comment_identity", sa.String(), nullable=False),
        sa.Column("expert_relative_path", sa.String(), nullable=False),
        sa.Column("reporter_outbox", sa.String(), nullable=False),
        sa.Column("required_mode", sa.String(), nullable=False),
        sa.Column("required_autotrading", sa.Boolean(), nullable=False),
        sa.Column("required_sizing_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id", "artifact_id"),
    )
    op.create_index(
        "ix_demo_chart_attachment_candidate_at",
        "demo_chart_attachment",
        ["candidate_id", "declared_at"],
    )
    op.execute("REVOKE UPDATE, DELETE ON demo_chart_attachment FROM stratos_app")


def downgrade() -> None:
    op.drop_index("ix_demo_chart_attachment_candidate_at", table_name="demo_chart_attachment")
    op.drop_table("demo_chart_attachment")

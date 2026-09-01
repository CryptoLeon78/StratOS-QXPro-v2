"""Inventario append-only de EAs externos observados."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9a4e1b2c3d4f"
down_revision: str | None = "b0a1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_ea_inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bot.id"), nullable=True),
        sa.Column("ea_filename", sa.String(), nullable=False),
        sa.Column("ea_relative_path", sa.String(), nullable=False),
        sa.Column("ea_sha256", sa.String(length=64), nullable=True),
        sa.Column("comment_identity", sa.String(), nullable=False),
        sa.Column("magic_number", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("timeframe", sa.String(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_external_ea_inventory_account_magic", "external_ea_inventory", ["account_id", "magic_number"])
    op.execute("REVOKE UPDATE, DELETE ON external_ea_inventory FROM stratos_app")


def downgrade() -> None:
    op.drop_index("ix_external_ea_inventory_account_magic", table_name="external_ea_inventory")
    op.drop_table("external_ea_inventory")

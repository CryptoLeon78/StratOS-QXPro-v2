"""G13: procedencia operacional e inventario de admision append-only."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b0a1c2d3e4f5"
down_revision: str | None = "d3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    account_origin = postgresql.ENUM(
        "BROKER_REAL", "BROKER_DEMO", "FIXTURE", name="account_data_origin"
    )
    bot_origin = postgresql.ENUM(
        "EXTERNAL_PRODUCTION", "INCUBATION", "ANALYSIS", name="bot_origin_kind"
    )
    asset_group = postgresql.ENUM("REAL", "INCUBATOR", "ANALYSIS", name="asset_source_group")
    asset_status = postgresql.ENUM(
        "DISCOVERED",
        "WITHHELD",
        "STATIC_VALIDATED",
        "BACKTEST_VALIDATED",
        "WAITING_CAPACITY",
        "INCUBATING",
        "CLASSIFIED",
        "REJECTED",
        name="asset_admission_status",
    )
    for enum in (account_origin, bot_origin, asset_group, asset_status):
        enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "account",
        sa.Column("data_origin", account_origin, nullable=False, server_default="FIXTURE"),
    )
    op.add_column(
        "bot",
        sa.Column("origin_kind", bot_origin, nullable=False, server_default="ANALYSIS"),
    )
    op.add_column("bot", sa.Column("incubation_grace_until", sa.DateTime(timezone=True)))
    op.create_table(
        "operational_asset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_group", postgresql.ENUM(name="asset_source_group", create_type=False), nullable=False),
        sa.Column("source_root", sa.String(), nullable=False),
        sa.Column("sqx_path", sa.String(), nullable=True),
        sa.Column("mql5_path", sa.String(), nullable=True),
        sa.Column("sqx_sha256", sa.String(length=64), nullable=True),
        sa.Column("mql5_sha256", sa.String(length=64), nullable=True),
        sa.Column("strategy_name", sa.String(), nullable=True),
        sa.Column("magic_number", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("timeframe", sa.String(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "operational_asset_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("operational_asset.id"), nullable=False),
        sa.Column("status", postgresql.ENUM(name="asset_admission_status", create_type=False), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operational_asset_event_asset_at", "operational_asset_event", ["asset_id", "occurred_at"])
    op.execute("REVOKE UPDATE, DELETE ON operational_asset, operational_asset_event FROM stratos_app")


def downgrade() -> None:
    op.drop_index("ix_operational_asset_event_asset_at", table_name="operational_asset_event")
    op.drop_table("operational_asset_event")
    op.drop_table("operational_asset")
    op.drop_column("bot", "incubation_grace_until")
    op.drop_column("bot", "origin_kind")
    op.drop_column("account", "data_origin")

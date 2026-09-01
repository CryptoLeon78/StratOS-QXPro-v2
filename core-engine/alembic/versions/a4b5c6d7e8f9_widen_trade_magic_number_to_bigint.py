"""Preserve full MT5 historical magic values in trades.

Revision ID: a4b5c6d7e8f9
Revises: f1b2c3d4e5f6
"""

from alembic import op
import sqlalchemy as sa


revision = "a4b5c6d7e8f9"
down_revision = "f1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # TimescaleDB prohibits ALTER COLUMN while a compression policy is
    # attached to the hypertable. This migration is transactional: restore
    # the same retention contract before commit.
    op.execute("SELECT remove_compression_policy('trade')")
    op.execute("ALTER TABLE trade SET (timescaledb.compress = false)")
    op.alter_column(
        "trade",
        "magic_number",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="magic_number::bigint",
        existing_nullable=False,
    )
    op.execute("ALTER TABLE trade SET (timescaledb.compress = true)")
    op.execute("SELECT add_compression_policy('trade', INTERVAL '90 days')")


def downgrade() -> None:
    op.execute("SELECT remove_compression_policy('trade')")
    op.execute("ALTER TABLE trade SET (timescaledb.compress = false)")
    op.alter_column(
        "trade",
        "magic_number",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="magic_number::integer",
        existing_nullable=False,
    )
    op.execute("ALTER TABLE trade SET (timescaledb.compress = true)")
    op.execute("SELECT add_compression_policy('trade', INTERVAL '90 days')")

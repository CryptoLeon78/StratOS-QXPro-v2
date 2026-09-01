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


def _decompress_trade_chunks() -> None:
    op.execute(
        """
        DO $$
        DECLARE chunk_name regclass;
        BEGIN
          FOR chunk_name IN
            SELECT format('%I.%I', c.chunk_schema, c.chunk_name)::regclass
            FROM timescaledb_information.chunks AS c
            WHERE c.hypertable_name = 'trade' AND c.is_compressed
          LOOP
            PERFORM decompress_chunk(chunk_name);
          END LOOP;
        END $$;
        """
    )


def _compress_trade_chunks() -> None:
    op.execute(
        """
        DO $$
        DECLARE chunk_name regclass;
        BEGIN
          FOR chunk_name IN
            SELECT format('%I.%I', c.chunk_schema, c.chunk_name)::regclass
            FROM timescaledb_information.chunks AS c
            WHERE c.hypertable_name = 'trade' AND c.range_end < now()
          LOOP
            PERFORM compress_chunk(chunk_name);
          END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    # TimescaleDB prohibits ALTER COLUMN while a compression policy is
    # attached to the hypertable. This migration is transactional: restore
    # the same retention contract before commit.
    op.execute("SELECT remove_compression_policy('trade')")
    _decompress_trade_chunks()
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
    _compress_trade_chunks()
    op.execute("SELECT add_compression_policy('trade', INTERVAL '90 days')")


def downgrade() -> None:
    op.execute("SELECT remove_compression_policy('trade')")
    _decompress_trade_chunks()
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
    _compress_trade_chunks()
    op.execute("SELECT add_compression_policy('trade', INTERVAL '90 days')")

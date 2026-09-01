"""G11: fills v1.1 inmutables para TCA."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2e8d801f42b"
down_revision: str | None = "f99b5d11e82e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_fill",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bot.id"), nullable=True),
        sa.Column("magic_number", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("type", postgresql.ENUM("BUY", "SELL", name="trade_type", create_type=False), nullable=False),
        sa.Column("volume", sa.Numeric(12, 4), nullable=False),
        sa.Column("requested_price", sa.Numeric(20, 10), nullable=False),
        sa.Column("executed_price", sa.Numeric(20, 10), nullable=False),
        sa.Column("spread", sa.Numeric(20, 10), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingest_batch_id", sa.Integer(), sa.ForeignKey("ingest_batch.id"), nullable=False),
        sa.UniqueConstraint("account_id", "order_id"),
    )
    op.execute("GRANT SELECT, INSERT ON execution_fill TO stratos_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE execution_fill_id_seq TO stratos_app")


def downgrade() -> None:
    op.drop_table("execution_fill")

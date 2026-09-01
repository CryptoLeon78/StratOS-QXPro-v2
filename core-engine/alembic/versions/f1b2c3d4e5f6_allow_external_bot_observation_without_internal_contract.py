"""Allow F7 external observations without fabricated internal sizing data."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f1b2c3d4e5f6"
down_revision: str | None = "9a4e1b2c3d4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("bot", "profile", existing_type=sa.String(), nullable=True)
    op.alter_column("bot", "capital_allocated_pct", existing_type=sa.Numeric(5, 2), nullable=True)
    op.alter_column("bot", "risk_per_trade_pct", existing_type=sa.Numeric(4, 3), nullable=True)
    op.create_check_constraint(
        "ck_bot_internal_contract_complete",
        "bot",
        "origin_kind = 'EXTERNAL_PRODUCTION' OR "
        "(profile IS NOT NULL AND capital_allocated_pct IS NOT NULL AND "
        "risk_per_trade_pct IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_bot_internal_contract_complete", "bot", type_="check")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM bot
                WHERE profile IS NULL
                   OR capital_allocated_pct IS NULL
                   OR risk_per_trade_pct IS NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade while external bot observations lack an internal contract';
            END IF;
        END $$;
        """
    )
    op.alter_column("bot", "risk_per_trade_pct", existing_type=sa.Numeric(4, 3), nullable=False)
    op.alter_column("bot", "capital_allocated_pct", existing_type=sa.Numeric(5, 2), nullable=False)
    op.alter_column("bot", "profile", existing_type=sa.String(), nullable=False)

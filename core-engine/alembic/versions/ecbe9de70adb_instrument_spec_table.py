"""instrument spec table

Revision ID: ecbe9de70adb
Revises: 0c2dfc843cea
Create Date: 2026-08-27 21:44:12.319509

G10 (docs/backlog.md): tick_size/tick_value/point_value por simbolo,
medidos de verdad contra MT5 -- importados de `user/data/data.db`
(INSTRUMENTS de SQX) via `scripts/import_instrument_specs.py`, no
inventados. Base de `r_multiple()` (PARTE 8).

El --autogenerate original tambien detecto (ruido, eliminado a mano, mismo
patron documentado en e215b505cf56/0c2dfc843cea): un create_foreign_key
duplicado de fk_bot_baseline_id (use_alter, ya existe desde la 0001) y 3
drop_index sobre indices que TimescaleDB crea el solo en las hypertables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ecbe9de70adb"
down_revision: Union[str, None] = "0c2dfc843cea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instrument_spec",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("tick_size", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("tick_value", sa.Numeric(precision=14, scale=6), nullable=False),
        sa.Column("point_value", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )


def downgrade() -> None:
    op.drop_table("instrument_spec")

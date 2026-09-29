"""alcance por cuenta (ADR 0013): account_id nullable en tablas de eventos

Aditiva: no reescribe filas (las tablas append-only no admiten UPDATE) --
NULL significa "evento heredado de portfolio". `correlation_snapshot_pair.n_obs`
guarda las observaciones comunes de cada par (NULL en snapshots anteriores).

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCOPED_TABLES = ("alert", "decision", "killswitch_event", "ums_phase_log", "withdrawal_log")


def upgrade() -> None:
    for table in _SCOPED_TABLES:
        op.add_column(table, sa.Column("account_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table}_account_id", table, "account", ["account_id"], ["id"])
        op.create_index(f"ix_{table}_account_id", table, ["account_id"])
    op.add_column("correlation_snapshot_pair", sa.Column("n_obs", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("correlation_snapshot_pair", "n_obs")
    for table in reversed(_SCOPED_TABLES):
        op.drop_index(f"ix_{table}_account_id", table_name=table)
        op.drop_constraint(f"fk_{table}_account_id", table, type_="foreignkey")
        op.drop_column(table, "account_id")

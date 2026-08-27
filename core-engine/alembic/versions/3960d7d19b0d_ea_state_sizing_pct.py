"""ea_state sizing_pct

Revision ID: 3960d7d19b0d
Revises: 89169958d9ac
Create Date: 2026-08-27 23:52:59.381649

G10 (docs/backlog.md): campo nuevo, opcional -- el contrato real de
PARTE 9.1 no lo pide todavia, el conector/EA actual no lo envia. Escrito
a spec para que config_drift.py compare sizing aplicado vs esperado el
dia que el EA lo reporte.

El --autogenerate original tambien detecto (ruido, eliminado a mano,
mismo patron documentado en migraciones previas de G10): un
create_foreign_key duplicado de fk_bot_baseline_id y 3 drop_index de
hypertables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3960d7d19b0d"
down_revision: Union[str, None] = "89169958d9ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ea_state", sa.Column("sizing_pct", sa.Numeric(precision=5, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column("ea_state", "sizing_pct")

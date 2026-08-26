"""widen bot sizing_current_pct to numeric 5 2

Revision ID: e215b505cf56
Revises: 385ebaaaaab5
Create Date: 2026-08-26 07:17:26.381247

PARTE 5.2 declara "sizing_current_pct NUMERIC(4,2) DEFAULT 100.0" pero
100.00 no cabe en NUMERIC(4,2) (max representable 99.99) - inconsistencia
real de la especificacion, encontrada al insertar un Bot con el default de
la propia factory de tests (asyncpg.exceptions.NumericValueOutOfRangeError).
Se amplia a NUMERIC(5,2).

El --autogenerate original tambien detecto (ruido, eliminado a mano):
un create_foreign_key duplicado de fk_bot_baseline_id (ya existe desde la
0001, es un FK use_alter que autogenerate redetecta como "nuevo") y 3
drop_index sobre los indices de tiempo que TimescaleDB crea el solo al
convertir trade/equity_snapshot/heartbeat_log en hypertables (no son
indices declarados por el modelo SQLAlchemy, aplicar esos DROP_INDEX
habria degradado las hypertables).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e215b505cf56'
down_revision: Union[str, None] = '385ebaaaaab5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('bot', 'sizing_current_pct',
               existing_type=sa.NUMERIC(precision=4, scale=2),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=False,
               existing_server_default=sa.text('100.0'))


def downgrade() -> None:
    op.alter_column('bot', 'sizing_current_pct',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.NUMERIC(precision=4, scale=2),
               existing_nullable=False,
               existing_server_default=sa.text('100.0'))

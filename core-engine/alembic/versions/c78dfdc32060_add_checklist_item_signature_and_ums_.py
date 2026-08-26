"""add checklist item signature and ums phase log signed_by

Revision ID: c78dfdc32060
Revises: 011e5ca44474
Create Date: 2026-08-26 19:51:45.195077

G5: `checklist_item_signature` es la tabla de staging mutable aprobada por
el operador para acumular las firmas item-a-item del checklist dominical/
mensual (PARTE 7.9/14) antes de escribir la fila unica e inmutable en
`checklist_run` (UNIQUE(checklist_type, period_key)). `ums_phase_log.
signed_by` es una columna nullable aditiva: NULL en una bajada automatica
de fase (protectora, sin firma), NOT NULL en un ascenso confirmado por el
operador (regla asimetrica de 7.9).

El --autogenerate detecto (ruido, eliminado a mano, mismo patron ya
documentado en e215b505cf56/011e5ca44474): el create_foreign_key duplicado
de fk_bot_baseline_id y los 3 drop_index sobre indices de tiempo que
TimescaleDB gestiona por su cuenta en las hypertables.

Tambien a mano: `postgresql.ENUM(..., create_type=False)` en
`checklist_item_signature.checklist_type` -- el tipo ENUM `checklist_type`
ya existe desde la migracion de `checklist_run` (governance.py); autogenerate
emite `sa.Enum(...)` generico y, sin `create_type=False` (que solo existe en
la clase `postgresql.ENUM`), `op.create_table` intenta `CREATE TYPE
checklist_type` de nuevo -> `DuplicateObjectError`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c78dfdc32060'
down_revision: Union[str, None] = '011e5ca44474'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('checklist_item_signature',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('checklist_type', postgresql.ENUM('SUNDAY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUAL', name='checklist_type', create_type=False), nullable=False),
    sa.Column('period_key', sa.String(), nullable=False),
    sa.Column('item_key', sa.String(), nullable=False),
    sa.Column('signed_by', sa.String(), nullable=False),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('checklist_type', 'period_key', 'item_key')
    )
    op.add_column('ums_phase_log', sa.Column('signed_by', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('ums_phase_log', 'signed_by')
    op.drop_table('checklist_item_signature')

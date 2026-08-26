"""add ea_state and virtual_trade tables

Revision ID: 011e5ca44474
Revises: e215b505cf56
Create Date: 2026-08-26 15:11:22.553250

G4 (PARTE 9.1): `POST /ingest/signals` y `POST /ingest/ea_state` no tenian
tabla destino entre las 25 de PARTE 5.2/G1 -- aprobado por el operador
ampliar el esquema con estas 2 tablas mutables (ni forman parte de las 6
tablas inmutables P6/P15.3, ni son hypertables: `ea_state` es upsert de
"ultimo estado conocido", no serie temporal).

El --autogenerate tambien detecto (ruido, eliminado a mano, mismo patron ya
documentado en e215b505cf56): un create_foreign_key duplicado de
fk_bot_baseline_id (ya existe desde la 0001, use_alter lo hace redetectarse
como "nuevo") y 3 drop_index sobre los indices de tiempo que TimescaleDB
crea solo al convertir trade/equity_snapshot/heartbeat_log en hypertables
(no son indices declarados por el modelo SQLAlchemy).

Tambien a mano: `postgresql.ENUM(..., create_type=False)` en la columna
`virtual_trade.type` -- el tipo ENUM `trade_type` ya existe desde
385ebaaaaab5 (columna `trade.type`); autogenerate emite `sa.Enum(...)`
generico (sin `create_type`, ese kwarg solo existe en
`sqlalchemy.dialects.postgresql.ENUM`), y sin marcarlo `op.create_table`
intenta `CREATE TYPE trade_type` otra vez -> `DuplicateObjectError`
(verificado con upgrade/downgrade/upgrade reales contra Postgres: el primer
intento con `sa.Enum(..., create_type=False)` seguia fallando porque ese
kwarg no existe en la clase generica y se ignoraba en silencio). `ea_state`
no usa ningun ENUM compartido, no le afecta.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011e5ca44474'
down_revision: Union[str, None] = 'e215b505cf56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ea_state',
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('magic_number', sa.Integer(), nullable=False),
    sa.Column('ea_version', sa.String(), nullable=False),
    sa.Column('mode', sa.String(), nullable=False),
    sa.Column('autotrading', sa.Boolean(), nullable=False),
    sa.Column('schedule_filter', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('news_windows', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ingest_batch_id', sa.Integer(), nullable=False),
    sa.Column('last_ingested_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.ForeignKeyConstraint(['ingest_batch_id'], ['ingest_batch.id'], ),
    sa.PrimaryKeyConstraint('account_id', 'magic_number')
    )
    op.create_table('virtual_trade',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('bot_id', sa.Integer(), nullable=True),
    sa.Column('magic_number', sa.Integer(), nullable=False),
    sa.Column('signal_id', sa.String(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('type', postgresql.ENUM('BUY', 'SELL', name='trade_type', create_type=False), nullable=False),
    sa.Column('volume', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('entry_price', sa.Numeric(precision=18, scale=5), nullable=False),
    sa.Column('sl', sa.Numeric(precision=18, scale=5), nullable=True),
    sa.Column('tp', sa.Numeric(precision=18, scale=5), nullable=True),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ingest_batch_id', sa.Integer(), nullable=False),
    sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.ForeignKeyConstraint(['bot_id'], ['bot.id'], ),
    sa.ForeignKeyConstraint(['ingest_batch_id'], ['ingest_batch.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id', 'magic_number', 'signal_id')
    )


def downgrade() -> None:
    op.drop_table('virtual_trade')
    op.drop_table('ea_state')

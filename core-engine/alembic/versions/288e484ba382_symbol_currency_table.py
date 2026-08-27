"""symbol currency table

Revision ID: 288e484ba382
Revises: ecbe9de70adb
Create Date: 2026-08-27 22:10:00.000000

G10 (docs/backlog.md, ASSUMPTIONS G5-08): divisa de exposicion por simbolo
-- base de `compute_exposure()` con subtotales por divisa. Los 10 simbolos
que StratOS siembra hoy, valores estandar de mercado (base de un par FX,
divisa de cotizacion/liquidacion de indices y materias primas) -- no una
tabla completa de instrumentos, solo los que StratOS ya opera. Se inserta
como datos de la propia migracion (10 filas, no justifica un script aparte
como `instrument_spec`).

El --autogenerate original tambien detecto (ruido, eliminado a mano, mismo
patron documentado en migraciones previas de G10): un create_foreign_key
duplicado de fk_bot_baseline_id y 3 drop_index de hypertables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "288e484ba382"
down_revision: Union[str, None] = "ecbe9de70adb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SYMBOL_CURRENCY = sa.table(
    "symbol_currency",
    sa.column("symbol", sa.String),
    sa.column("currency", sa.String),
)

# base del par FX, o divisa de cotizacion/liquidacion del indice/materia
# prima -- verificado a mano contra convencion estandar de mercado.
_ROWS = [
    {"symbol": "EURUSD", "currency": "EUR"},
    {"symbol": "GBPUSD", "currency": "GBP"},
    {"symbol": "USDJPY", "currency": "USD"},
    {"symbol": "XAUUSD", "currency": "USD"},
    {"symbol": "XAGUSD", "currency": "USD"},
    {"symbol": "GDAXI", "currency": "EUR"},
    {"symbol": "NDX", "currency": "USD"},
    {"symbol": "SPX500", "currency": "USD"},
    {"symbol": "US30", "currency": "USD"},
    {"symbol": "USOIL", "currency": "USD"},
]


def upgrade() -> None:
    op.create_table(
        "symbol_currency",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.bulk_insert(_SYMBOL_CURRENCY, _ROWS)


def downgrade() -> None:
    op.drop_table("symbol_currency")

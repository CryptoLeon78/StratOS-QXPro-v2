"""widen r_multiple precision

Revision ID: 89169958d9ac
Revises: 288e484ba382
Create Date: 2026-08-27 22:41:06.406481

G10 (docs/backlog.md): backfill_r_multiple.py, corrido de verdad contra
Postgres local, disparo un overflow real -- NUMERIC(8,4) (max abs 9999.9999)
se queda corto para indices con SL muy ajustado frente a su tick_size
(GDAXI/NDX/SPX500/US30 sembrados con precios no realistas, R hasta ~6.8e4
medido). Ampliado a NUMERIC(12,4), headroom generoso sobre lo observado.

`trade` es una hypertable comprimida (migracion 0001/385ebaaaaab5, PARTE
5.2, `compress_segmentby='bot_id'` + politica de compresion a 90 dias) --
`ALTER COLUMN ... TYPE` no esta soportado ni con los chunks descomprimidos
mientras el reloption `timescaledb.compress` siga activo en la hypertable
(2 `FeatureNotSupportedError` reales distintos, verificados contra Postgres
local antes de dar con la secuencia correcta). Hace falta: descomprimir
chunks -> quitar la politica de compresion -> desactivar
`timescaledb.compress` -> alterar la columna -> reactivar compresion con
el MISMO `compress_segmentby` -> re-anadir la politica con el MISMO
intervalo -> recomprimir los chunks. Mismo mecanismo documentado ya en
ASSUMPTIONS G9 para el caso analogo de `pg_restore`/FK en hypertables
comprimidas.

El --autogenerate original tambien detecto (ruido, eliminado a mano, mismo
patron documentado en migraciones previas de G10): un create_foreign_key
duplicado de fk_bot_baseline_id y 3 drop_index de hypertables.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "89169958d9ac"
down_revision: Union[str, None] = "288e484ba382"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SELECT decompress_chunk(c, if_compressed => true) FROM show_chunks('trade') c")
    op.execute("SELECT remove_compression_policy('trade')")
    op.execute("ALTER TABLE trade SET (timescaledb.compress = false)")
    op.execute("ALTER TABLE trade ALTER COLUMN r_multiple TYPE NUMERIC(12, 4)")
    op.execute(
        "ALTER TABLE trade SET (timescaledb.compress, timescaledb.compress_segmentby = 'bot_id')"
    )
    op.execute("SELECT add_compression_policy('trade', INTERVAL '90 days')")
    op.execute("SELECT compress_chunk(c, if_not_compressed => true) FROM show_chunks('trade') c")


def downgrade() -> None:
    op.execute("SELECT decompress_chunk(c, if_compressed => true) FROM show_chunks('trade') c")
    op.execute("SELECT remove_compression_policy('trade')")
    op.execute("ALTER TABLE trade SET (timescaledb.compress = false)")
    op.execute("ALTER TABLE trade ALTER COLUMN r_multiple TYPE NUMERIC(8, 4)")
    op.execute(
        "ALTER TABLE trade SET (timescaledb.compress, timescaledb.compress_segmentby = 'bot_id')"
    )
    op.execute("SELECT add_compression_policy('trade', INTERVAL '90 days')")
    op.execute("SELECT compress_chunk(c, if_not_compressed => true) FROM show_chunks('trade') c")

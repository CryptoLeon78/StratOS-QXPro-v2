"""Importa tick_size/tick_value/point_value reales por simbolo a
`instrument_spec` (G10, docs/backlog.md).

Fuente: `user/data/data.db` (SQLite, INSTRUMENTS de SQX) -- los mismos
TICKSIZE/POINTVALUE que `Apps_entorno_SQX/spread_sqx` mide y valida contra
MT5 real (app propia ya en produccion, ver `spread_sqx/mt5_spread.py` y
`spread_sqx/contrato.py`). Lectura SQLite de solo lectura (`mode=ro`):
segura aunque SQX este abierto/minando -- la exigencia de "SQX cerrado" de
`spread_sqx/destino_db.py` solo aplica a sus rutas de ESCRITURA, que aqui
no se usan.

`tick_value = POINTVALUE * TICKSIZE` (inverso de
`spread_sqx/unidades.py::pointvalue_desde_mt5`, que calcula
`POINTVALUE = tick_value / tick_size`).

Solo se importan instrumentos con sufijo `_darwinex` (unico broker real de
StratOS, PARTE 13) -- el resto de las ~980 filas de INSTRUMENTS son de
otros brokers/proyectos de SQX, fuera de alcance. Re-ejecutable (UPSERT
por simbolo), no destructivo.

Uso:
    PYTHONPATH=core-engine/src:scripts python scripts/import_instrument_specs.py
    PYTHONPATH=core-engine/src:scripts python scripts/import_instrument_specs.py \
        --data-db /ruta/a/data.db
"""

import argparse
import asyncio
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import core.db.models  # noqa: F401 -- registra las tablas en Base.metadata
from core.db.base import async_session_factory
from core.db.models.market import InstrumentSpec
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

_SOURCE = "sqx_data_db"
_SUFFIX = "_darwinex"

# scripts/import_instrument_specs.py -> scripts/ -> StratOS-QXPro-v2/ ->
# Apps_entorno_SQX/ -> SQX_144_Full2/ -> user/data/data.db
_DEFAULT_DATA_DB = Path(__file__).resolve().parents[3] / "user" / "data" / "data.db"

# El nombre que StratOS usa en Trade.symbol (PARTE 13) no siempre coincide
# con el INSTRUMENT de SQX una vez quitado el sufijo de broker -- verificado
# a mano contra Apps_entorno_SQX/SQX_vs_MT5_Panel/sqx_mt5_config.py::DATA
# (la tabla DATA de data.db es la fuente autoritativa del mapeo real
# SYMBOL/INSTRUMENT/USYMBOL, mismo mecanismo que ya usa ese panel propio).
# Los 7 simbolos restantes de StratOS coinciden letra a letra sin necesitar
# esta tabla -- estos 3 son la excepcion real, no una regla general.
_ALIAS = {
    "SPX500": "SP500",
    "US30": "WS30",
    "USOIL": "XTIUSD",
}


def _read_darwinex_specs(data_db: Path) -> dict[str, tuple[Decimal, Decimal]]:
    """{simbolo_stratos: (tick_size, point_value)} para cada INSTRUMENT que
    termina en `_darwinex`, con TICKSIZE/POINTVALUE no nulos."""
    con = sqlite3.connect(f"file:{data_db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT INSTRUMENT, TICKSIZE, POINTVALUE FROM INSTRUMENTS "
            "WHERE INSTRUMENT LIKE ? AND TICKSIZE IS NOT NULL AND POINTVALUE IS NOT NULL",
            (f"%{_SUFFIX}",),
        ).fetchall()
    finally:
        con.close()

    alias_sqx_a_stratos = {sqx: stratos for stratos, sqx in _ALIAS.items()}
    specs: dict[str, tuple[Decimal, Decimal]] = {}
    for instrument, ticksize, pointvalue in rows:
        sqx_symbol = instrument[: -len(_SUFFIX)]
        symbol = alias_sqx_a_stratos.get(sqx_symbol, sqx_symbol)
        specs[symbol] = (Decimal(str(ticksize)), Decimal(str(pointvalue)))
    return specs


async def import_instrument_specs(data_db: Path) -> int:
    """Importa/actualiza instrument_spec. Devuelve cuantos simbolos se
    importaron/actualizaron."""
    if not data_db.exists():
        raise FileNotFoundError(f"no se encuentra data.db: {data_db}")

    specs = _read_darwinex_specs(data_db)
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        for symbol, (tick_size, point_value) in specs.items():
            tick_value = point_value * tick_size
            stmt = (
                insert(InstrumentSpec)
                .values(
                    symbol=symbol,
                    tick_size=tick_size,
                    tick_value=tick_value,
                    point_value=point_value,
                    source=_SOURCE,
                    imported_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["symbol"],
                    set_={
                        "tick_size": tick_size,
                        "tick_value": tick_value,
                        "point_value": point_value,
                        "source": _SOURCE,
                        "imported_at": now,
                    },
                )
            )
            await session.execute(stmt)
        await session.commit()

    return len(specs)


async def _report_unmatched_trade_symbols() -> list[str]:
    """Simbolos que StratOS ya tiene en Trade pero instrument_spec no cubre
    -- r_multiple se queda NULL para esos, documentado, no inventado."""
    from core.db.models.market import Trade

    async with async_session_factory() as session:
        trade_symbols = set(
            (await session.execute(select(Trade.symbol).distinct())).scalars().all()
        )
        spec_symbols = set((await session.execute(select(InstrumentSpec.symbol))).scalars().all())
    return sorted(trade_symbols - spec_symbols)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-db", type=Path, default=_DEFAULT_DATA_DB)
    args = parser.parse_args()

    n_imported = await import_instrument_specs(args.data_db)
    print(
        f"[import_instrument_specs] importados/actualizados: {n_imported} (fuente: {args.data_db})"
    )

    unmatched = await _report_unmatched_trade_symbols()
    if unmatched:
        print(
            f"[import_instrument_specs] simbolos de Trade SIN spec (r_multiple se queda NULL): "
            f"{', '.join(unmatched)}"
        )
    else:
        print("[import_instrument_specs] todos los simbolos de Trade tienen spec")


if __name__ == "__main__":
    asyncio.run(main())

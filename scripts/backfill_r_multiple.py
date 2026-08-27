"""Recalcula `Trade.r_multiple` para todos los trades cerrados con `sl`
no nulo (G10, docs/backlog.md) usando `formulas/trading.py::r_multiple`
(ya existe, PARTE 8) + `instrument_spec` (G10, importado de SQX via
`import_instrument_specs.py`). Re-ejecutable: recalcula y SOBRESCRIBE (no
solo rellena NULLs) -- si `instrument_spec` se actualiza con datos mas
recientes, este script propaga el nuevo tick_value/tick_size.

`profit_net = Trade.profit + Trade.commission + Trade.swap` (P&L neto
real, incluye costes de la operacion) -- PARTE 8 no fija esta suma
explicitamente para `r_multiple` a nivel de trade individual; decision
propia documentada aqui y en ASSUMPTIONS G10 (mismo criterio que
`core/ingest/services/trades.py` usa al poblar `r_multiple` para los
trades nuevos desde el ingest).

Trades sin `sl`, o cuyo `symbol` no tiene fila en `instrument_spec`, se
quedan con `r_multiple` NULL -- no se inventa.

Uso:
    PYTHONPATH=core-engine/src python scripts/backfill_r_multiple.py
"""

import asyncio
from decimal import Decimal

import core.db.models  # noqa: F401 -- registra las tablas en Base.metadata
from core.db.base import async_session_factory
from core.db.models.market import InstrumentSpec, Trade
from core.formulas.trading import r_multiple
from sqlalchemy import select


def r_multiple_for_trade(
    profit: Decimal,
    commission: Decimal,
    swap: Decimal,
    entry: Decimal,
    sl: Decimal | None,
    volume: Decimal,
    spec: tuple[Decimal, Decimal] | None,
) -> Decimal | None:
    """Logica pura, sin BBDD: `spec` es `(tick_value, tick_size)` o `None`
    si el simbolo no tiene fila en `instrument_spec`."""
    if spec is None or sl is None:
        return None
    tick_value, tick_size = spec
    profit_net = profit + commission + swap
    return r_multiple(
        profit_net=profit_net,
        entry=entry,
        sl=sl,
        volume=volume,
        tick_value=tick_value,
        tick_size=tick_size,
    )


async def backfill_r_multiple() -> tuple[int, set[str]]:
    """Devuelve `(trades_actualizados, simbolos_sin_spec)`."""
    async with async_session_factory() as session:
        specs: dict[str, tuple[Decimal, Decimal]] = {
            row.symbol: (row.tick_value, row.tick_size)
            for row in (await session.execute(select(InstrumentSpec))).scalars().all()
        }

        trades = (
            (
                await session.execute(
                    select(Trade).where(Trade.close_time.isnot(None), Trade.sl.isnot(None))
                )
            )
            .scalars()
            .all()
        )

        updated = 0
        without_spec: set[str] = set()
        for trade in trades:
            spec = specs.get(trade.symbol)
            if spec is None:
                without_spec.add(trade.symbol)
                continue
            trade.r_multiple = r_multiple_for_trade(
                profit=trade.profit,
                commission=trade.commission,
                swap=trade.swap,
                entry=trade.open_price,
                sl=trade.sl,
                volume=trade.volume,
                spec=spec,
            )
            updated += 1

        await session.commit()
        return updated, without_spec


async def main() -> None:
    updated, without_spec = await backfill_r_multiple()
    print(f"[backfill_r_multiple] trades actualizados: {updated}")
    if without_spec:
        print(
            f"[backfill_r_multiple] simbolos sin instrument_spec (r_multiple sigue NULL): "
            f"{', '.join(sorted(without_spec))}"
        )
    else:
        print("[backfill_r_multiple] todos los trades cerrados con sl tienen spec")


if __name__ == "__main__":
    asyncio.run(main())

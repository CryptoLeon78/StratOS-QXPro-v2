"""PARTE 9.1: `POST /ingest/trades` -- deals cerrados (`history_deals_get`).
Idempotente (P9) via `ON CONFLICT (ticket_mt5, open_time)`: si la fila ya
existe Y ya esta cerrada (`close_time IS NOT NULL`), un reenvio no toca
nada (duplicado real); si existe pero seguia abierta (la creo antes
`/ingest/positions`), esta es la primera vez que se reporta el cierre ->
se actualiza. `bot_id NULL` = huerfano, la ingesta nunca se rechaza por eso
(PARTE 5.2).

`r_multiple` (G10, docs/backlog.md) se calcula aqui mismo, en el momento
del cierre, via `formulas/trading.py::r_multiple_net_of_costs` +
`instrument_spec` (ya importado de SQX, `scripts/import_instrument_specs.py`)
-- sin fila de spec para el simbolo, o sin `sl`, se queda NULL (no se
inventa). Misma convencion que `scripts/backfill_r_multiple.py` usa para
los trades historicos ya cerrados antes de este commit."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account, Bot
from core.db.models.market import InstrumentSpec, Trade
from core.formulas.trading import r_multiple_net_of_costs
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import TradesIngestRequest
from core.ingest.services import IngestOutcome

BOT_MAGIC_MIN = -(2**31)
BOT_MAGIC_MAX = 2**31 - 1


async def _resolve_bot_id(session: AsyncSession, account_id: int, magic_number: int) -> int | None:
    # 0 está reservado por el importador HTML para “magic no expuesto”; no es
    # un magic MT5 válido ni puede resolver un bot por coincidencia.
    if magic_number == 0 or not BOT_MAGIC_MIN <= magic_number <= BOT_MAGIC_MAX:
        return None
    result = await session.execute(
        select(Bot.id).where(Bot.account_id == account_id, Bot.magic_number == magic_number)
    )
    return result.scalar_one_or_none()


async def _instrument_specs(
    session: AsyncSession, symbols: set[str]
) -> dict[str, tuple[Decimal, Decimal]]:
    if not symbols:
        return {}
    rows = (
        await session.execute(
            select(
                InstrumentSpec.symbol, InstrumentSpec.tick_value, InstrumentSpec.tick_size
            ).where(InstrumentSpec.symbol.in_(symbols))
        )
    ).all()
    return {symbol: (tick_value, tick_size) for symbol, tick_value, tick_size in rows}


async def ingest_trades(
    session: AsyncSession, account: Account, req: TradesIngestRequest
) -> IngestOutcome:
    batch, ya_visto = await seal_and_create_batch(
        session,
        account,
        batch_type="trades",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.trades),
    )
    if ya_visto:
        # Sello ya registrado: el lote es byte a byte el mismo y no hay nada
        # que ingerir. El intento queda sellado igual (traza append-only);
        # lo que se salta es el reproceso de sus registros.
        return IngestOutcome(
            accepted=0,
            duplicated=len(req.trades),
            batch_id=batch.id,
            server_time=batch.server_ts,
        )

    now = datetime.now(UTC)
    specs = await _instrument_specs(session, {trade.symbol for trade in req.trades})
    accepted = 0
    for trade in req.trades:
        bot_id = await _resolve_bot_id(session, account.id, trade.magic_number)
        spec = specs.get(trade.symbol)
        r_multiple = (
            r_multiple_net_of_costs(
                profit=trade.profit,
                commission=trade.commission,
                swap=trade.swap,
                entry=trade.open_price,
                sl=trade.sl,
                volume=trade.volume,
                tick_value=spec[0],
                tick_size=spec[1],
            )
            if spec is not None
            else None
        )
        stmt = (
            pg_insert(Trade)
            .values(
                bot_id=bot_id,
                account_id=account.id,
                magic_number=trade.magic_number,
                ticket_mt5=trade.ticket_mt5,
                symbol=trade.symbol,
                open_time=trade.open_time,
                close_time=trade.close_time,
                type=trade.type,
                volume=trade.volume,
                open_price=trade.open_price,
                close_price=trade.close_price,
                sl=trade.sl,
                tp=trade.tp,
                profit=trade.profit,
                commission=trade.commission,
                swap=trade.swap,
                r_multiple=r_multiple,
                ingest_batch_id=batch.id,
                ingested_at=now,
            )
            .on_conflict_do_update(
                index_elements=["ticket_mt5", "open_time"],
                set_={
                    "close_time": trade.close_time,
                    "close_price": trade.close_price,
                    "profit": trade.profit,
                    "commission": trade.commission,
                    "swap": trade.swap,
                    "r_multiple": r_multiple,
                },
                where=Trade.close_time.is_(None),
            )
            .returning(Trade.id)
        )
        result = await session.execute(stmt)
        if result.first() is not None:
            accepted += 1

    return IngestOutcome(
        accepted=accepted,
        duplicated=len(req.trades) - accepted,
        batch_id=batch.id,
        server_time=batch.server_ts,
    )

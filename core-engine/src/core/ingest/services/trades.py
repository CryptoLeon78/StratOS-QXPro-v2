"""PARTE 9.1: `POST /ingest/trades` -- deals cerrados (`history_deals_get`).
Idempotente (P9) via `ON CONFLICT (ticket_mt5, open_time)`: si la fila ya
existe Y ya esta cerrada (`close_time IS NOT NULL`), un reenvio no toca
nada (duplicado real); si existe pero seguia abierta (la creo antes
`/ingest/positions`), esta es la primera vez que se reporta el cierre ->
se actualiza. `bot_id NULL` = huerfano, la ingesta nunca se rechaza por eso
(PARTE 5.2)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account, Bot
from core.db.models.market import Trade
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import TradesIngestRequest
from core.ingest.services import IngestOutcome


async def _resolve_bot_id(session: AsyncSession, account_id: int, magic_number: int) -> int | None:
    result = await session.execute(
        select(Bot.id).where(Bot.account_id == account_id, Bot.magic_number == magic_number)
    )
    return result.scalar_one_or_none()


async def ingest_trades(
    session: AsyncSession, account: Account, req: TradesIngestRequest
) -> IngestOutcome:
    batch = await seal_and_create_batch(
        session,
        account,
        batch_type="trades",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.trades),
    )

    now = datetime.now(UTC)
    accepted = 0
    for trade in req.trades:
        bot_id = await _resolve_bot_id(session, account.id, trade.magic_number)
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

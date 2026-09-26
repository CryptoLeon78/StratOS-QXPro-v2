"""PARTE 9.1: `POST /ingest/signals` -- trades virtuales (semaforo NARANJA,
PARTE 6.1). Persiste en `VirtualTrade` (G4, migracion 011e), nunca en
`Trade` (mezclar senales virtuales con P&L real corrompería cualquier
formula que escanee la tabla)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account, Bot
from core.db.models.market import VirtualTrade
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import SignalsIngestRequest
from core.ingest.services import IngestOutcome


async def _resolve_bot_id(session: AsyncSession, account_id: int, magic_number: int) -> int | None:
    result = await session.execute(
        select(Bot.id).where(Bot.account_id == account_id, Bot.magic_number == magic_number)
    )
    return result.scalar_one_or_none()


async def ingest_signals(
    session: AsyncSession, account: Account, req: SignalsIngestRequest
) -> IngestOutcome:
    batch, ya_visto = await seal_and_create_batch(
        session,
        account,
        batch_type="signals",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.signals),
    )
    if ya_visto:
        # Sello ya registrado: el lote es byte a byte el mismo y no hay nada
        # que ingerir. El intento queda sellado igual (traza append-only);
        # lo que se salta es el reproceso de sus registros.
        return IngestOutcome(
            accepted=0,
            duplicated=len(req.signals),
            batch_id=batch.id,
            server_time=batch.server_ts,
        )

    now = datetime.now(UTC)
    bot_id = await _resolve_bot_id(session, account.id, req.magic)
    accepted = 0
    for signal in req.signals:
        stmt = (
            pg_insert(VirtualTrade)
            .values(
                account_id=account.id,
                bot_id=bot_id,
                magic_number=req.magic,
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                type=signal.type,
                volume=signal.volume,
                entry_price=signal.entry_price,
                sl=signal.sl,
                tp=signal.tp,
                ts=signal.ts,
                ingest_batch_id=batch.id,
                ingested_at=now,
            )
            .on_conflict_do_nothing(index_elements=["account_id", "magic_number", "signal_id"])
            .returning(VirtualTrade.id)
        )
        result = await session.execute(stmt)
        if result.first() is not None:
            accepted += 1

    return IngestOutcome(
        accepted=accepted,
        duplicated=len(req.signals) - accepted,
        batch_id=batch.id,
        server_time=batch.server_ts,
    )

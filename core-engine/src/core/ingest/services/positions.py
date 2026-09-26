"""PARTE 9.1: `POST /ingest/positions` -- snapshot de posiciones abiertas
(`positions_get`, cada 5s). No existe tabla Position separada (PARTE 5.2):
upsert guardado sobre `Trade`, mismo criterio que `/ingest/trades`
(`ON CONFLICT ... WHERE close_time IS NULL` -- una posicion ya cerrada
nunca se resucita por una actualizacion tardia en carrera entre pollers).
Si no hay fila previa, es la primera vez que se ve esa posicion abierta.

P5 (PARTE 2): posicion sin SL -> `Alert` CRITICA inline, misma transaccion,
en TODA posicion de TODO snapshot (no solo la primera vez -- el SL puede
desaparecer/reaparecer entre polls). Si una posicion que antes no tenia SL
ahora si lo trae, se resuelve la alerta que la propia ingesta creo."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel
from core.db.models.accounts import Account, Bot
from core.db.models.decisions import Alert
from core.db.models.market import Trade
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import PositionIn, PositionsIngestRequest
from core.ingest.services import IngestOutcome

_ZERO = Decimal("0")


def _missing_sl_dedup_key(account_id: int, ticket_mt5: int) -> str:
    return f"ingest_missing_sl:{account_id}:{ticket_mt5}"


async def _resolve_bot_id(session: AsyncSession, account_id: int, magic_number: int) -> int | None:
    result = await session.execute(
        select(Bot.id).where(Bot.account_id == account_id, Bot.magic_number == magic_number)
    )
    return result.scalar_one_or_none()


async def _apply_p5_check(
    session: AsyncSession, account_id: int, position: PositionIn, now: datetime
) -> None:
    dedup_key = _missing_sl_dedup_key(account_id, position.ticket_mt5)
    existing = (
        await session.execute(
            select(Alert).where(Alert.dedup_key == dedup_key, Alert.resolved.is_(False))
        )
    ).scalar_one_or_none()

    missing_sl = position.sl is None or position.sl == _ZERO
    if missing_sl:
        if existing is None:
            session.add(
                Alert(
                    ts=now,
                    level=AlertLevel.CRITICA,
                    module="ingest_positions",
                    message=f"Posicion {position.ticket_mt5} ({position.symbol}) sin stop loss.",
                    action_required="Colocar SL de inmediato (P5).",
                    dedup_key=dedup_key,
                )
            )
    elif existing is not None:
        existing.resolved = True
        existing.resolved_at = now
        existing.resolved_by = "system:ingest"


async def ingest_positions(
    session: AsyncSession, account: Account, req: PositionsIngestRequest
) -> IngestOutcome:
    batch, ya_visto = await seal_and_create_batch(
        session,
        account,
        batch_type="positions",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.positions),
    )
    if ya_visto:
        # Sello ya registrado: el lote es byte a byte el mismo y no hay nada
        # que ingerir. El intento queda sellado igual (traza append-only);
        # lo que se salta es el reproceso de sus registros.
        return IngestOutcome(
            accepted=0,
            duplicated=len(req.positions),
            batch_id=batch.id,
            server_time=batch.server_ts,
        )

    now = datetime.now(UTC)
    accepted = 0
    for position in req.positions:
        bot_id = await _resolve_bot_id(session, account.id, position.magic_number)
        stmt = (
            pg_insert(Trade)
            .values(
                bot_id=bot_id,
                account_id=account.id,
                magic_number=position.magic_number,
                ticket_mt5=position.ticket_mt5,
                symbol=position.symbol,
                open_time=position.open_time,
                close_time=None,
                type=position.type,
                volume=position.volume,
                open_price=position.open_price,
                close_price=None,
                sl=position.sl,
                tp=position.tp,
                profit=position.profit,
                commission=_ZERO,
                swap=_ZERO,
                ingest_batch_id=batch.id,
                ingested_at=now,
            )
            .on_conflict_do_update(
                index_elements=["ticket_mt5", "open_time"],
                set_={"sl": position.sl, "tp": position.tp, "profit": position.profit},
                where=Trade.close_time.is_(None),
            )
            .returning(Trade.id)
        )
        result = await session.execute(stmt)
        if result.first() is not None:
            accepted += 1

        await _apply_p5_check(session, account.id, position, now)

    return IngestOutcome(
        accepted=accepted,
        duplicated=len(req.positions) - accepted,
        batch_id=batch.id,
        server_time=batch.server_ts,
    )

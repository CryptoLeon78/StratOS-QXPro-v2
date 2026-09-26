"""PARTE 9.1: `POST /ingest/ea_state` -- espejo del ULTIMO estado conocido
por EA (`EaState`, PK `(account_id, magic_number)`, UPSERT real, no serie
temporal). Alimenta Cuentas/EA (7.2)."""

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account
from core.db.models.market import EaState
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import EaStateIngestRequest
from core.ingest.services import IngestOutcome
from core.services.demo_attachment import advance_verified_f3_candidates


async def ingest_ea_state(
    session: AsyncSession, account: Account, req: EaStateIngestRequest, redis: Redis
) -> IngestOutcome:
    batch, ya_visto = await seal_and_create_batch(
        session,
        account,
        batch_type="ea_state",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.eas),
    )
    if ya_visto:
        # Sello ya registrado: el lote es byte a byte el mismo y no hay nada
        # que ingerir. El intento queda sellado igual (traza append-only);
        # lo que se salta es el reproceso de sus registros.
        return IngestOutcome(
            accepted=0,
            duplicated=len(req.eas),
            batch_id=batch.id,
            server_time=batch.server_ts,
        )

    now = datetime.now(UTC)
    for ea in req.eas:
        stmt = pg_insert(EaState).values(
            account_id=account.id,
            magic_number=ea.magic,
            ea_version=ea.ea_version,
            mode=ea.mode,
            autotrading=ea.autotrading,
            schedule_filter=ea.schedule_filter,
            news_windows=ea.news_windows,
            sizing_pct=ea.sizing_pct,
            ingest_batch_id=batch.id,
            last_ingested_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["account_id", "magic_number"],
            set_={
                "ea_version": ea.ea_version,
                "mode": ea.mode,
                "autotrading": ea.autotrading,
                "schedule_filter": ea.schedule_filter,
                "news_windows": ea.news_windows,
                "sizing_pct": ea.sizing_pct,
                "ingest_batch_id": batch.id,
                "last_ingested_at": now,
            },
        )
        await session.execute(stmt)

    # The upsert has to be flushed before F3 admission reads the fresh reporter
    # snapshot. It advances only candidates that satisfy the sealed contract.
    await session.flush()
    await advance_verified_f3_candidates(session, redis, account, [ea.magic for ea in req.eas])

    # "espejo de estado actual", no "log append-only": un reenvio siempre
    # re-confirma el estado vigente, no hay nocion de "duplicado" real aqui
    # (distinto de los otros 6 endpoints -- ver docstring de IngestResponse
    # / ASSUMPTIONS G4).
    return IngestOutcome(
        accepted=len(req.eas), duplicated=0, batch_id=batch.id, server_time=batch.server_ts
    )

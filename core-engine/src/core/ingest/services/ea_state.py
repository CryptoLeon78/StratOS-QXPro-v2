"""PARTE 9.1: `POST /ingest/ea_state` -- espejo del ULTIMO estado conocido
por EA (`EaState`, PK `(account_id, magic_number)`, UPSERT real, no serie
temporal). Alimenta Cuentas/EA (7.2)."""

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account
from core.db.models.market import EaState
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import EaStateIngestRequest
from core.ingest.services import IngestOutcome


async def ingest_ea_state(
    session: AsyncSession, account: Account, req: EaStateIngestRequest
) -> IngestOutcome:
    batch = await seal_and_create_batch(
        session,
        account,
        batch_type="ea_state",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.eas),
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

    # "espejo de estado actual", no "log append-only": un reenvio siempre
    # re-confirma el estado vigente, no hay nocion de "duplicado" real aqui
    # (distinto de los otros 6 endpoints -- ver docstring de IngestResponse
    # / ASSUMPTIONS G4).
    return IngestOutcome(
        accepted=len(req.eas), duplicated=0, batch_id=batch.id, server_time=batch.server_ts
    )

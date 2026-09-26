"""PARTE 9.1: `POST /ingest/heartbeat`. `status` se fija a `"OK"` -- no hay
umbral en `SystemConfig` para clasificar latencia como degradada/critica
(eso es watchdog, G5); sin ninguna rama que decida entre valores, "OK" es
una constante de modulo, no un umbral P11."""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account
from core.db.models.market import HeartbeatLog
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import HeartbeatIngestRequest
from core.ingest.services import IngestOutcome

_STATUS_OK = "OK"


async def ingest_heartbeat(
    session: AsyncSession, account: Account, req: HeartbeatIngestRequest
) -> IngestOutcome:
    batch, ya_visto = await seal_and_create_batch(
        session,
        account,
        batch_type="heartbeat",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=1,
    )
    if ya_visto:
        # Sello ya registrado: el lote es byte a byte el mismo y no hay nada
        # que ingerir. El intento queda sellado igual (traza append-only);
        # lo que se salta es el reproceso de sus registros.
        return IngestOutcome(
            accepted=0,
            duplicated=1,
            batch_id=batch.id,
            server_time=batch.server_ts,
        )

    stmt = (
        pg_insert(HeartbeatLog)
        .values(
            ts=req.ts,
            connector_instance_id=req.connector_instance_id,
            account_id=account.id,
            latency_ms=req.latency_ms,
            status=_STATUS_OK,
        )
        .on_conflict_do_nothing(index_elements=["ts", "connector_instance_id", "account_id"])
        .returning(HeartbeatLog.ts)
    )
    result = await session.execute(stmt)
    accepted = 1 if result.first() is not None else 0

    return IngestOutcome(
        accepted=accepted, duplicated=1 - accepted, batch_id=batch.id, server_time=batch.server_ts
    )

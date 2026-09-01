"""PARTE 9.1: `POST /ingest/execution` -- v1.1 del EA reporter (TCA:
requested vs executed, spread). Contrato ya definido, "sin consumidor
aun" (literal de PARTE 9.1): solo sella el lote, no persiste `fills`
todavia -- no hay tabla destino ni consumidor real hasta que el EA v1.1
exista."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account, Bot
from core.db.models.market import ExecutionFill
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import ExecutionIngestRequest
from core.ingest.services import IngestOutcome


async def ingest_execution(
    session: AsyncSession, account: Account, req: ExecutionIngestRequest
) -> IngestOutcome:
    batch = await seal_and_create_batch(
        session,
        account,
        batch_type="execution",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=len(req.fills),
    )
    bot_id = (
        await session.execute(
            select(Bot.id).where(Bot.account_id == account.id, Bot.magic_number == req.magic)
        )
    ).scalar_one_or_none()
    rows = [
        {
            "account_id": account.id,
            "bot_id": bot_id,
            "magic_number": req.magic,
            "order_id": fill.order_id,
            "symbol": fill.symbol,
            "type": fill.type,
            "volume": fill.volume,
            "requested_price": fill.requested_price,
            "status": fill.status,
            "rejection_reason": fill.rejection_reason,
            "executed_price": fill.executed_price,
            "spread": fill.spread,
            "ts": fill.ts,
            "ingest_batch_id": batch.id,
        }
        for fill in req.fills
    ]
    if not rows:
        return IngestOutcome(
            accepted=0,
            duplicated=0,
            batch_id=batch.id,
            server_time=batch.server_ts,
        )
    statement = (
        insert(ExecutionFill)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["account_id", "order_id"])
        .returning(ExecutionFill.id)
    )
    inserted = len((await session.execute(statement)).scalars().all())
    return IngestOutcome(
        accepted=inserted,
        duplicated=len(rows) - inserted,
        batch_id=batch.id,
        server_time=batch.server_ts,
    )

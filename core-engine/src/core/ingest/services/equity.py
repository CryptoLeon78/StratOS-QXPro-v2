"""PARTE 9.1: `POST /ingest/equity`. `drawdown_pct` (NOT NULL en
`EquitySnapshot`) no viene en el payload -- PARTE 8 tampoco define una
formula para "un punto nuevo contra el pico historico" (`max_drawdown_pct`
opera sobre una curva completa ya cerrada). Diseno propio, documentado en
ASSUMPTIONS G4: pico = max(equity historico del account, equity nuevo);
drawdown = (pico - nuevo) / pico * 100, nunca negativo."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account
from core.db.models.market import EquitySnapshot
from core.ingest.batch import seal_and_create_batch
from core.ingest.schemas import EquityIngestRequest
from core.ingest.services import IngestOutcome

_ZERO_DD = Decimal("0.000")


async def _current_drawdown_pct(
    session: AsyncSession, account_id: int, new_equity: Decimal
) -> Decimal:
    result = await session.execute(
        select(func.max(EquitySnapshot.equity)).where(EquitySnapshot.account_id == account_id)
    )
    peak = result.scalar_one_or_none()
    if peak is None or new_equity > peak:
        peak = new_equity
    if peak <= 0:
        return _ZERO_DD
    drawdown = (peak - new_equity) / peak * 100
    return max(_ZERO_DD, drawdown).quantize(_ZERO_DD)


async def ingest_equity(
    session: AsyncSession, account: Account, req: EquityIngestRequest
) -> IngestOutcome:
    batch = await seal_and_create_batch(
        session,
        account,
        batch_type="equity",
        account_login=req.account_login,
        connector_instance_id=req.connector_instance_id,
        claimed_sha256=req.batch_sha256,
        records=[req.model_dump(mode="json", exclude={"batch_sha256"})],
        record_count=1,
    )

    drawdown_pct = await _current_drawdown_pct(session, account.id, req.equity)
    stmt = (
        pg_insert(EquitySnapshot)
        .values(
            ts=req.ts,
            account_id=account.id,
            equity=req.equity,
            balance=req.balance,
            drawdown_pct=drawdown_pct,
            margin_level=req.margin_level,
            free_margin=req.free_margin,
        )
        .on_conflict_do_nothing(index_elements=["ts", "account_id"])
        .returning(EquitySnapshot.ts)
    )
    result = await session.execute(stmt)
    accepted = 1 if result.first() is not None else 0

    return IngestOutcome(
        accepted=accepted, duplicated=1 - accepted, batch_id=batch.id, server_time=batch.server_ts
    )

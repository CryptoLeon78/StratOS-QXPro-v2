"""PARTE 9.2: `GET /api/v1/audit/status` + `POST /audit/run` + `GET
/audit/seals` -- pestaña Auditoria (7.11). Reutiliza `audit.py`
(core/services/, ya existe, G5)."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.accounts import Account
from core.redis import get_redis
from core.services.audit import (
    AuditConfig,
    ReconciliationResult,
    SealsSummary,
    compute_reconciliation,
    compute_seals_summary,
    run_audit_daily,
)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"], dependencies=[Depends(get_current_user)])

_AUDIT_CONFIG = AuditConfig()


class ReconciliationResponse(BaseModel):
    account_id: int
    initial_balance: Decimal
    flows: Decimal
    final_balance: Decimal
    expected: Decimal
    discrepancy_pct: Decimal | None
    breached: bool

    model_config = {"from_attributes": True}


class SealsSummaryResponse(BaseModel):
    total_batches: int
    total_trades: int
    ticket_min: int | None
    ticket_max: int | None
    history_start: datetime | None
    history_end: datetime | None

    model_config = {"from_attributes": True}


async def _status(session: AsyncSession) -> list[ReconciliationResult]:
    account_ids = (
        (await session.execute(select(Account.id).where(Account.is_active.is_(True))))
        .scalars()
        .all()
    )
    results = []
    for account_id in account_ids:
        result = await compute_reconciliation(session, account_id, _AUDIT_CONFIG)
        if result is not None:
            results.append(result)
    return results


@router.get("/status", response_model=list[ReconciliationResponse])
async def audit_status(session: AsyncSession = Depends(get_session)) -> list[ReconciliationResult]:
    return await _status(session)


@router.post("/run", response_model=list[ReconciliationResponse])
async def audit_run(
    session: AsyncSession = Depends(get_session), redis: Redis = Depends(get_redis)
) -> list[ReconciliationResult]:
    await run_audit_daily(session, redis, _AUDIT_CONFIG, datetime.now(UTC))
    await session.commit()
    return await _status(session)


@router.get("/seals", response_model=SealsSummaryResponse)
async def audit_seals(session: AsyncSession = Depends(get_session)) -> SealsSummary:
    return await compute_seals_summary(session)

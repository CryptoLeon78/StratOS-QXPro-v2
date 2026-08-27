"""PARTE 9.2: `GET /api/v1/audit/status` + `POST /audit/run` + `GET
/audit/seals` -- pestaña Auditoria (7.11). Reutiliza `audit.py`
(core/services/, ya existe, G5).

`GET /audit/continuity-gaps` (G10, docs/backlog.md): `compute_send_
continuity()` ya calculaba `gaps` con detalle por tramo (desde G5) -- solo
`coverage_pct` se exponia (via `/execution/heartbeat`), sin ruta que
devolviera el detalle. No es una formula nueva, solo faltaba el wiring."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
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
    compute_send_continuity,
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


class ContinuityGapResponse(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: float


class ContinuityGapsResponse(BaseModel):
    account_id: int
    coverage_pct: float
    gaps: list[ContinuityGapResponse]


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


@router.get("/continuity-gaps", response_model=list[ContinuityGapsResponse])
async def audit_continuity_gaps(
    days: int = Query(default=_AUDIT_CONFIG.continuity_window_days),
    session: AsyncSession = Depends(get_session),
) -> list[ContinuityGapsResponse]:
    now = datetime.now(UTC)
    account_ids = (await session.execute(select(Account.id))).scalars().all()
    result = []
    for account_id in account_ids:
        continuity = await compute_send_continuity(session, account_id, _AUDIT_CONFIG, days, now)
        result.append(
            ContinuityGapsResponse(
                account_id=continuity.account_id,
                coverage_pct=continuity.coverage_pct,
                gaps=[
                    ContinuityGapResponse(
                        start=gap.start, end=gap.end, duration_minutes=gap.duration_minutes
                    )
                    for gap in continuity.gaps
                ],
            )
        )
    return result

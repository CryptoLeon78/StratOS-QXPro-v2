"""PARTE 9.2: `GET /api/v1/accounts` + `/{id}/eas` + `/drift` -- pestaña
Cuentas/EA (7.2, diseño derivado sin captura). `/drift` reutiliza
`config_drift.py::compute_drift` (ya existe, G5).

`equity`/`balance`/`free_margin`/`margin_level` en `AccountResponse` (G10,
docs/backlog.md): el `EquitySnapshot` mas reciente por `account_id` (ya
existe, G1) -- `None` si la cuenta nunca ha reportado un snapshot."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.accounts import Account
from core.db.models.market import EaState, EquitySnapshot
from core.services.config_drift import compute_drift

router = APIRouter(
    prefix="/api/v1/accounts", tags=["accounts"], dependencies=[Depends(get_current_user)]
)


class AccountResponse(BaseModel):
    id: int
    name: str
    broker: str
    login: str
    server: str
    currency: str
    is_demo: bool
    is_active: bool
    equity: Decimal | None
    balance: Decimal | None
    free_margin: Decimal | None
    margin_level: float | None
    equity_ts: datetime | None


class EaStateResponse(BaseModel):
    magic_number: int
    ea_version: str
    mode: str
    autotrading: bool
    schedule_filter: dict[str, Any] | None
    news_windows: list[Any] | None
    sizing_pct: Decimal | None
    last_ingested_at: datetime

    model_config = {"from_attributes": True}


class DriftRowResponse(BaseModel):
    bot_id: int
    account_id: int
    magic_number: int
    expected_mode: str
    reported_mode: str
    drift: bool
    expected_sizing_pct: Decimal
    reported_sizing_pct: Decimal | None
    sizing_drift: bool | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AccountResponse])
async def list_accounts(session: AsyncSession = Depends(get_session)) -> list[AccountResponse]:
    accounts = (await session.execute(select(Account))).scalars().all()
    latest_by_account = {
        snapshot.account_id: snapshot
        for snapshot in (
            await session.execute(
                select(EquitySnapshot)
                .distinct(EquitySnapshot.account_id)
                .order_by(EquitySnapshot.account_id, EquitySnapshot.ts.desc())
            )
        )
        .scalars()
        .all()
    }
    result = []
    for account in accounts:
        snapshot = latest_by_account.get(account.id)
        result.append(
            AccountResponse(
                id=account.id,
                name=account.name,
                broker=account.broker,
                login=account.login,
                server=account.server,
                currency=account.currency,
                is_demo=account.is_demo,
                is_active=account.is_active,
                equity=snapshot.equity if snapshot else None,
                balance=snapshot.balance if snapshot else None,
                free_margin=snapshot.free_margin if snapshot else None,
                margin_level=snapshot.margin_level if snapshot else None,
                equity_ts=snapshot.ts if snapshot else None,
            )
        )
    return result


@router.get("/drift", response_model=list[DriftRowResponse])
async def account_drift(session: AsyncSession = Depends(get_session)) -> list[DriftRowResponse]:
    rows = await compute_drift(session)
    return [DriftRowResponse.model_validate(row) for row in rows]


@router.get("/{account_id}/eas", response_model=list[EaStateResponse])
async def list_eas(account_id: int, session: AsyncSession = Depends(get_session)) -> list[EaState]:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cuenta no encontrada")
    return list(
        (await session.execute(select(EaState).where(EaState.account_id == account_id)))
        .scalars()
        .all()
    )

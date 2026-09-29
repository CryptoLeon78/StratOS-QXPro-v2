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
from core.db.enums import AccountDataOrigin
from core.db.models.accounts import Account, Bot
from core.db.models.market import EaState, EquitySnapshot
from core.routers.scope import AccountScope
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
    data_origin: AccountDataOrigin
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
    ea_required_version: str | None
    version_verifiable: bool
    version_matches: bool | None


class DriftRowResponse(BaseModel):
    bot_id: int
    account_id: int
    magic_number: int
    expected_mode: str
    reported_mode: str
    drift: bool
    expected_autotrading: bool
    reported_autotrading: bool
    autotrading_drift: bool
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
                data_origin=account.data_origin,
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
async def account_drift(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> list[DriftRowResponse]:
    rows = await compute_drift(session)
    return [
        DriftRowResponse.model_validate(row)
        for row in rows
        if account_id is None or row.account_id == account_id
    ]


@router.get("/{account_id}/eas", response_model=list[EaStateResponse])
async def list_eas(
    account_id: int, session: AsyncSession = Depends(get_session)
) -> list[EaStateResponse]:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cuenta no encontrada")
    eas = list(
        (await session.execute(select(EaState).where(EaState.account_id == account_id)))
        .scalars()
        .all()
    )
    required_versions = {
        bot.magic_number: bot.ea_required_version
        for bot in (await session.execute(select(Bot).where(Bot.account_id == account_id)))
        .scalars()
        .all()
    }
    return [
        EaStateResponse(
            magic_number=ea.magic_number,
            ea_version=ea.ea_version,
            mode=ea.mode,
            autotrading=ea.autotrading,
            schedule_filter=ea.schedule_filter,
            news_windows=ea.news_windows,
            sizing_pct=ea.sizing_pct,
            last_ingested_at=ea.last_ingested_at,
            ea_required_version=required_versions.get(ea.magic_number),
            version_verifiable=required_versions.get(ea.magic_number) is not None,
            version_matches=(
                ea.ea_version == required_versions[ea.magic_number]
                if required_versions.get(ea.magic_number) is not None
                else None
            ),
        )
        for ea in eas
    ]

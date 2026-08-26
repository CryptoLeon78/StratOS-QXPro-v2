"""PARTE 9.2: `GET /api/v1/accounts` + `/{id}/eas` + `/drift` -- pestaña
Cuentas/EA (7.2, diseño derivado sin captura). `/drift` reutiliza
`config_drift.py::compute_drift` (ya existe, G5)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.accounts import Account
from core.db.models.market import EaState
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

    model_config = {"from_attributes": True}


class EaStateResponse(BaseModel):
    magic_number: int
    ea_version: str
    mode: str
    autotrading: bool
    schedule_filter: dict[str, Any] | None
    news_windows: list[Any] | None
    last_ingested_at: datetime

    model_config = {"from_attributes": True}


class DriftRowResponse(BaseModel):
    bot_id: int
    account_id: int
    magic_number: int
    expected_mode: str
    reported_mode: str
    drift: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AccountResponse])
async def list_accounts(session: AsyncSession = Depends(get_session)) -> list[Account]:
    return list((await session.execute(select(Account))).scalars().all())


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

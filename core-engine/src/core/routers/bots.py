"""PARTE 9.2: `GET /api/v1/bots` + `/{id}` + `/{id}/semaphore-history` --
pestaña Bots (7.4, layout maestro-detalle). Query directa."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import BotProfile, BotRole, PipelinePhase, SemaphoreState
from core.db.models.accounts import Bot
from core.db.models.decisions import SemaphoreTransition

router = APIRouter(prefix="/api/v1/bots", tags=["bots"], dependencies=[Depends(get_current_user)])


class BotResponse(BaseModel):
    id: int
    account_id: int
    magic_number: int
    name: str
    market: str
    timeframe: str
    profile: BotProfile
    role: BotRole
    slot: str | None
    pipeline_phase: PipelinePhase
    semaphore_state: SemaphoreState
    entered_state_at: datetime
    capital_allocated_pct: Decimal
    risk_per_trade_pct: Decimal
    sizing_multiplier: Decimal
    sizing_current_pct: Decimal
    kelly_fraction: Decimal | None
    created_at: datetime
    baseline_id: int | None

    model_config = {"from_attributes": True}


class SemaphoreHistoryRow(BaseModel):
    id: int
    ts: datetime
    from_state: SemaphoreState
    to_state: SemaphoreState
    trigger_metrics: dict[str, Any]
    instruction_text: str
    confirmed_at: datetime | None
    confirmed_by: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BotResponse])
async def list_bots(session: AsyncSession = Depends(get_session)) -> list[Bot]:
    return list((await session.execute(select(Bot))).scalars().all())


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: int, session: AsyncSession = Depends(get_session)) -> Bot:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    return bot


@router.get("/{bot_id}/semaphore-history", response_model=list[SemaphoreHistoryRow])
async def semaphore_history(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> list[SemaphoreTransition]:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    return list(
        (
            await session.execute(
                select(SemaphoreTransition)
                .where(SemaphoreTransition.bot_id == bot_id)
                .order_by(SemaphoreTransition.ts.desc())
            )
        )
        .scalars()
        .all()
    )

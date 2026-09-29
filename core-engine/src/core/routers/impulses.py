"""PARTE 9.2: `GET/POST /api/v1/impulses` + `/impulses/report?quarter=` --
modulo transversal "Diario de impulsos" (7.11). Reutiliza `impulses.py`
(core/services/, ya existe, G5)."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import ImpulseAction, ImpulseStatus
from core.db.models.accounts import Bot
from core.db.models.decisions import ImpulseLog
from core.routers.scope import AccountScope
from core.services.impulses import ImpulseReport, create_impulse, quarterly_report

router = APIRouter(
    prefix="/api/v1/impulses", tags=["impulses"], dependencies=[Depends(get_current_user)]
)


class ImpulseResponse(BaseModel):
    id: int
    ts: datetime
    bot_id: int
    description: str
    desired_action: ImpulseAction
    executed: bool
    status: ImpulseStatus
    counterfactual_result_7d_eur: Decimal | None
    avoided_cost_eur: Decimal | None
    evaluated_at: datetime | None

    model_config = {"from_attributes": True}


class CreateImpulseRequest(BaseModel):
    bot_id: int
    description: str
    desired_action: ImpulseAction


class ImpulseReportResponse(BaseModel):
    quarter: str
    count: int
    total_avoided_cost_eur: Decimal

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ImpulseResponse])
async def list_impulses(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> list[ImpulseLog]:
    query = select(ImpulseLog).order_by(ImpulseLog.ts.desc())
    if account_id is not None:
        query = query.join(Bot, Bot.id == ImpulseLog.bot_id).where(Bot.account_id == account_id)
    return list((await session.execute(query)).scalars().all())


@router.post("", response_model=ImpulseResponse, status_code=status.HTTP_201_CREATED)
async def post_impulse(
    body: CreateImpulseRequest, session: AsyncSession = Depends(get_session)
) -> ImpulseLog:
    bot = await session.get(Bot, body.bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    impulse = await create_impulse(
        session, body.bot_id, body.description, body.desired_action, datetime.now(UTC)
    )
    await session.commit()
    return impulse


@router.get("/report", response_model=ImpulseReportResponse)
async def impulse_report(
    quarter: str, session: AsyncSession = Depends(get_session)
) -> ImpulseReport:
    return await quarterly_report(session, quarter)

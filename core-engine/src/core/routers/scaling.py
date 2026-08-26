"""PARTE 9.2: `GET /api/v1/scaling/ums` + `/monthly` -- pestaña Escalado
(7.9). Reutiliza `ums.py::current_phase` (ya existe, G5)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.governance import UmsPhaseLog
from core.services.ums import current_phase

router = APIRouter(
    prefix="/api/v1/scaling", tags=["scaling"], dependencies=[Depends(get_current_user)]
)


class UmsPhaseResponse(BaseModel):
    id: int
    ts: datetime
    phase: int
    equity_at: Decimal
    metrics: dict[str, Any]
    ready_to_advance: bool
    signed_by: str | None

    model_config = {"from_attributes": True}


@router.get("/ums", response_model=UmsPhaseResponse | None)
async def scaling_ums(session: AsyncSession = Depends(get_session)) -> UmsPhaseLog | None:
    return await current_phase(session)


@router.get("/monthly", response_model=list[UmsPhaseResponse])
async def scaling_monthly(session: AsyncSession = Depends(get_session)) -> list[UmsPhaseLog]:
    return list(
        (await session.execute(select(UmsPhaseLog).order_by(UmsPhaseLog.ts.asc()))).scalars().all()
    )

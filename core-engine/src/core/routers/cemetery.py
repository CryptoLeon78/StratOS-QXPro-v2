"""PARTE 9.2: `GET /api/v1/cemetery` (+ reactivacion: 409 SIEMPRE). PARTE
6.3 literal: "Reactivacion: API 409 siempre; sin control en UI" -- usa
`evaluate_cemetery_reactivation` (ya existe, G3), que por diseño devuelve
`allowed=False` para cualquier input, sin excepcion posible."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import CemeteryCause, PipelinePhase
from core.db.models.pipeline import CemeteryEntry
from core.state_machines.challenger import evaluate_cemetery_reactivation
from core.state_machines.types import ChallengerConfig

router = APIRouter(
    prefix="/api/v1/cemetery", tags=["cemetery"], dependencies=[Depends(get_current_user)]
)

_CHALLENGER_CONFIG = ChallengerConfig()


class CemeteryEntryResponse(BaseModel):
    id: int
    bot_id: int
    retired_at: datetime
    cause: CemeteryCause
    autopsy_text: str
    lesson: str
    revalidation_from_phase: PipelinePhase
    reactivation_blocked: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CemeteryEntryResponse])
async def list_cemetery(session: AsyncSession = Depends(get_session)) -> list[CemeteryEntry]:
    return list((await session.execute(select(CemeteryEntry))).scalars().all())


@router.post("/{bot_id}/reactivate")
async def reactivate(bot_id: int) -> None:
    result = evaluate_cemetery_reactivation(bot_id, _CHALLENGER_CONFIG)
    raise HTTPException(status.HTTP_409_CONFLICT, result.reason)

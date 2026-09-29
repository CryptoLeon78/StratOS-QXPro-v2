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
from core.db.models.accounts import Bot
from core.db.models.pipeline import CemeteryEntry, PipelineCandidate, PipelinePhaseTransition
from core.routers.scope import AccountScope
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
    entered_pipeline_at: datetime | None = None

    model_config = {"from_attributes": True}


async def _entered_pipeline_at(session: AsyncSession, bot_id: int) -> datetime | None:
    """Fecha real de entrada a F1, desde el rastro append-only `PipelinePhaseTransition`
    (existe desde G11, ver `docs/adr/0006`). `from_phase IS NULL` marca la transicion de
    alta -- es unica por candidato porque solo se escribe una vez, en `create_candidate`.

    Devuelve `None` para un bot retirado sin ese rastro (admitido antes de G11, o sin
    `PipelineCandidate`): ausencia declarada, nunca `Bot.created_at` como sustituto -- no
    todos los bots pasan por F1-F7."""
    candidate_id = await session.scalar(
        select(PipelineCandidate.id).where(PipelineCandidate.bot_id == bot_id)
    )
    if candidate_id is None:
        return None
    return await session.scalar(
        select(PipelinePhaseTransition.occurred_at).where(
            PipelinePhaseTransition.candidate_id == candidate_id,
            PipelinePhaseTransition.from_phase.is_(None),
        )
    )


@router.get("", response_model=list[CemeteryEntryResponse])
async def list_cemetery(
    account_id: AccountScope,
    session: AsyncSession = Depends(get_session),
) -> list[CemeteryEntryResponse]:
    entries_query = select(CemeteryEntry)
    if account_id is not None:
        entries_query = entries_query.join(Bot, Bot.id == CemeteryEntry.bot_id).where(
            Bot.account_id == account_id
        )
    entries = list((await session.execute(entries_query)).scalars().all())
    return [
        CemeteryEntryResponse.model_validate(entry).model_copy(
            update={"entered_pipeline_at": await _entered_pipeline_at(session, entry.bot_id)}
        )
        for entry in entries
    ]


@router.post("/{bot_id}/reactivate")
async def reactivate(bot_id: int) -> None:
    result = evaluate_cemetery_reactivation(bot_id, _CHALLENGER_CONFIG)
    raise HTTPException(status.HTTP_409_CONFLICT, result.reason)

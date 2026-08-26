"""PARTE 9.2: `GET /api/v1/pipeline/board` + `POST /candidates` +
`/{id}/promote` + `/{id}/kill` + `GET /{id}/gate` -- pestaña Pipeline
(7.3, kanban de 7 columnas). Ascensos F1-F3 son manuales (este router);
F4+ SOLO por gate automatico (6.3) -- `promote` los rechaza con 409, el
unico camino real es `pipeline_gate.py::evaluate_and_persist` (barrido,
ya existe G5). `kill` reutiliza `apply_cemetery_archival` (G3, ya existe:
autopsia obligatoria, valida antes de tocar la sesion)."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import CemeteryCause, PipelinePhase, Verdict
from core.db.models.accounts import Bot
from core.db.models.pipeline import CemeteryEntry, PipelineCandidate
from core.redis import get_redis
from core.state_machines.challenger import apply_cemetery_archival

router = APIRouter(
    prefix="/api/v1/pipeline", tags=["pipeline"], dependencies=[Depends(get_current_user)]
)

_MANUAL_PHASES = (PipelinePhase.F1, PipelinePhase.F2, PipelinePhase.F3)
_PHASE_ORDER = [
    PipelinePhase.F1,
    PipelinePhase.F2,
    PipelinePhase.F3,
    PipelinePhase.F4,
    PipelinePhase.F5,
    PipelinePhase.F6,
    PipelinePhase.F7,
]


class CandidateResponse(BaseModel):
    id: int
    bot_id: int
    current_phase: PipelinePhase
    entered_phase_at: datetime
    incubation_days: int
    oos_trades: int
    profit_factor: float | None
    expectancy_r: float | None
    sharpe: float | None
    max_dd_pct: Decimal | None
    wfe: float | None
    trades_per_week: float | None
    gates_passed: int
    gates_total: int
    provisional: bool
    verdict: Verdict | None
    verdict_reason: str | None
    decision_eta_days: int | None
    evaluated_at: datetime | None

    model_config = {"from_attributes": True}


class CreateCandidateRequest(BaseModel):
    bot_id: int


class KillRequest(BaseModel):
    cause: CemeteryCause
    autopsy_text: str
    lesson: str


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


async def _get_candidate(session: AsyncSession, candidate_id: int) -> PipelineCandidate:
    candidate = await session.get(PipelineCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidato no encontrado")
    return candidate


@router.get("/board", response_model=list[CandidateResponse])
async def pipeline_board(session: AsyncSession = Depends(get_session)) -> list[PipelineCandidate]:
    return list((await session.execute(select(PipelineCandidate))).scalars().all())


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    body: CreateCandidateRequest, session: AsyncSession = Depends(get_session)
) -> PipelineCandidate:
    bot = await session.get(Bot, body.bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    candidate = PipelineCandidate(
        bot_id=body.bot_id,
        current_phase=PipelinePhase.F1,
        entered_phase_at=datetime.now(UTC),
        incubation_days=0,
        oos_trades=0,
    )
    session.add(candidate)
    await session.commit()
    return candidate


@router.post("/{candidate_id}/promote", response_model=CandidateResponse)
async def promote_candidate(
    candidate_id: int, session: AsyncSession = Depends(get_session)
) -> PipelineCandidate:
    candidate = await _get_candidate(session, candidate_id)
    if candidate.current_phase not in _MANUAL_PHASES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ascensos F4+ solo por gate automatico (PARTE 6.3), no manual",
        )
    next_index = _PHASE_ORDER.index(candidate.current_phase) + 1
    candidate.current_phase = _PHASE_ORDER[next_index]
    candidate.entered_phase_at = datetime.now(UTC)
    await session.commit()
    return candidate


@router.post("/{candidate_id}/kill", response_model=CemeteryEntryResponse)
async def kill_candidate(
    candidate_id: int,
    body: KillRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> CemeteryEntry:
    candidate = await _get_candidate(session, candidate_id)
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")

    try:
        await apply_cemetery_archival(
            session, redis, bot, body.cause, body.autopsy_text, body.lesson
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    candidate.current_phase = PipelinePhase.CEMENTERIO
    await session.commit()

    entry = (
        await session.execute(select(CemeteryEntry).where(CemeteryEntry.bot_id == bot.id))
    ).scalar_one()
    return entry


@router.get("/{candidate_id}/gate", response_model=CandidateResponse)
async def candidate_gate(
    candidate_id: int, session: AsyncSession = Depends(get_session)
) -> PipelineCandidate:
    return await _get_candidate(session, candidate_id)

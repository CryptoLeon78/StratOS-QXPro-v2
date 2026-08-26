"""PARTE 9.2: `GET /api/v1/decisions` + `POST /{id}/confirm|postpone|dismiss`
-- alimenta "Requiere accion (N)" del Resumen (7.1) y el `DecisionCard`.
Query/CRUD directo, sin services/ propio (Decision es la unica tabla
involucrada, sin logica de negocio mas alla de la transicion de estado)."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import DecisionStatus
from core.db.models.decisions import Decision
from core.db.models.governance import User

router = APIRouter(
    prefix="/api/v1/decisions", tags=["decisions"], dependencies=[Depends(get_current_user)]
)


class DecisionResponse(BaseModel):
    id: int
    ts: datetime
    module: str
    title: str
    description: str
    instruction_text: str
    evidence: dict[str, Any] | None
    status: DecisionStatus
    decided_at: datetime | None
    decided_by: str | None
    postpone_until: datetime | None

    model_config = {"from_attributes": True}


class PostponeRequest(BaseModel):
    postpone_until: datetime


async def _get_pending_decision(session: AsyncSession, decision_id: int) -> Decision:
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "decision no encontrada")
    if decision.status != DecisionStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"decision ya resuelta ({decision.status.value})"
        )
    return decision


@router.get("", response_model=list[DecisionResponse])
async def list_decisions(
    decision_status: DecisionStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Decision]:
    query = select(Decision).order_by(Decision.ts.desc())
    if decision_status is not None:
        query = query.where(Decision.status == decision_status)
    return list((await session.execute(query)).scalars().all())


@router.post("/{decision_id}/confirm", response_model=DecisionResponse)
async def confirm_decision(
    decision_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Decision:
    decision = await _get_pending_decision(session, decision_id)
    decision.status = DecisionStatus.CONFIRMED
    decision.decided_at = datetime.now(UTC)
    decision.decided_by = user.email
    await session.commit()
    return decision


@router.post("/{decision_id}/postpone", response_model=DecisionResponse)
async def postpone_decision(
    decision_id: int,
    body: PostponeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Decision:
    decision = await _get_pending_decision(session, decision_id)
    decision.status = DecisionStatus.POSTPONED
    decision.decided_at = datetime.now(UTC)
    decision.decided_by = user.email
    decision.postpone_until = body.postpone_until
    await session.commit()
    return decision


@router.post("/{decision_id}/dismiss", response_model=DecisionResponse)
async def dismiss_decision(
    decision_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Decision:
    decision = await _get_pending_decision(session, decision_id)
    decision.status = DecisionStatus.DISMISSED
    decision.decided_at = datetime.now(UTC)
    decision.decided_by = user.email
    await session.commit()
    return decision

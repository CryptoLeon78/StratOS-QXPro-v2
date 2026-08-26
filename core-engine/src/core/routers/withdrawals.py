"""PARTE 9.2: `GET /api/v1/withdrawals/calculator` + `POST /withdrawals`
-- pestaña Escalado/protocolo de retiros (7.9/14). Reutiliza
`withdrawals.py` (core/services/, ya existe, G5)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import ChecklistType
from core.db.models.governance import ChecklistRun, WithdrawalLog
from core.services.risk import real_portfolio_equity_curve
from core.services.withdrawals import WithdrawalServiceConfig, calculate, register_withdrawal

router = APIRouter(
    prefix="/api/v1/withdrawals", tags=["withdrawals"], dependencies=[Depends(get_current_user)]
)

_CONFIG = WithdrawalServiceConfig()


class CalculatorResponse(BaseModel):
    suggested_amount_eur: Decimal


class RegisterWithdrawalRequest(BaseModel):
    amount: Decimal
    checklist_type: ChecklistType
    period_key: str


class WithdrawalLogResponse(BaseModel):
    id: int
    ts: datetime
    amount: Decimal
    equity_before: Decimal

    model_config = {"from_attributes": True}


@router.get("/calculator", response_model=CalculatorResponse)
async def withdrawals_calculator(
    session: AsyncSession = Depends(get_session),
) -> CalculatorResponse:
    amount = await calculate(session, _CONFIG, datetime.now(UTC))
    return CalculatorResponse(suggested_amount_eur=amount)


@router.post("", response_model=WithdrawalLogResponse)
async def register(
    body: RegisterWithdrawalRequest, session: AsyncSession = Depends(get_session)
) -> WithdrawalLog:
    checklist = (
        await session.execute(
            select(ChecklistRun).where(
                ChecklistRun.checklist_type == body.checklist_type,
                ChecklistRun.period_key == body.period_key,
            )
        )
    ).scalar_one_or_none()
    if checklist is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "checklist del periodo no encontrado o no completado"
        )

    now = datetime.now(UTC)
    curve = await real_portfolio_equity_curve(session, now - timedelta(days=30))
    equity_before = Decimal(str(curve.iloc[-1])) if not curve.empty else Decimal("0")

    try:
        log = await register_withdrawal(session, body.amount, checklist, equity_before, now)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await session.commit()
    return log

"""PARTE 9.2: `GET /api/v1/risk/tail` + `/exposure` + `/montecarlo` --
pestaña Riesgo (7.7). Reutiliza `risk.py`/`montecarlo.py` (core/services/,
ya existen, G5) -- ningun recalculo sincrono en el request, solo lo ya
persistido/computable bajo demanda con los datos actuales."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.governance import MonteCarloRun
from core.routers.scope import AccountScope
from core.services.risk import (
    RiskServiceConfig,
    compute_exposure,
    compute_tail_risk,
    exposure_pnl_eur,
    exposure_subtotals_by_currency,
)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"], dependencies=[Depends(get_current_user)])

_RISK_CONFIG = RiskServiceConfig()


class TailRiskResponse(BaseModel):
    var95_daily: float
    var99_daily: float
    cvar95_daily: float
    cvar99_daily: float
    var99_monthly: float
    cvar99_monthly: float
    cvar99_annual: float
    breached: bool
    verdict: str

    model_config = {"from_attributes": True}


class ExposureRowResponse(BaseModel):
    symbol: str
    net_volume: Decimal
    gross_volume: Decimal
    pnl: Decimal
    currency: str | None

    model_config = {"from_attributes": True}


class ExposureCurrencySubtotalResponse(BaseModel):
    currency: str
    net_volume: Decimal
    gross_volume: Decimal
    pnl: Decimal

    model_config = {"from_attributes": True}


class ExposureEurResponse(BaseModel):
    pnl_eur: Decimal
    unconverted_currencies: list[str]


class MonteCarloResponse(BaseModel):
    bot_id: int
    ts: datetime
    n_simulations: int
    dd_p50: Decimal
    dd_p75: Decimal
    dd_p95: Decimal
    dd_contract_pct: Decimal
    seed: int

    model_config = {"from_attributes": True}


@router.get("/tail", response_model=TailRiskResponse | None)
async def risk_tail(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> TailRiskResponse | None:
    result = await compute_tail_risk(session, _RISK_CONFIG, datetime.now(UTC), account_id)
    return TailRiskResponse.model_validate(result) if result is not None else None


@router.get("/exposure", response_model=list[ExposureRowResponse])
async def risk_exposure(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> list[ExposureRowResponse]:
    rows = await compute_exposure(session, account_id)
    return [ExposureRowResponse.model_validate(row) for row in rows]


@router.get("/exposure/by-currency", response_model=list[ExposureCurrencySubtotalResponse])
async def risk_exposure_by_currency(
    account_id: AccountScope,
    session: AsyncSession = Depends(get_session),
) -> list[ExposureCurrencySubtotalResponse]:
    rows = await compute_exposure(session, account_id)
    subtotals = exposure_subtotals_by_currency(rows)
    return [ExposureCurrencySubtotalResponse.model_validate(s) for s in subtotals.values()]


@router.get("/exposure/eur", response_model=ExposureEurResponse)
async def risk_exposure_eur(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> ExposureEurResponse:
    rows = await compute_exposure(session, account_id)
    result = await exposure_pnl_eur(session, rows)
    return ExposureEurResponse(
        pnl_eur=result.pnl_eur,
        unconverted_currencies=sorted(result.unconverted_currencies),
    )


@router.get("/montecarlo", response_model=MonteCarloResponse | None)
async def risk_montecarlo(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> MonteCarloRun | None:
    return (
        await session.execute(
            select(MonteCarloRun)
            .where(MonteCarloRun.bot_id == bot_id)
            .order_by(MonteCarloRun.ts.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@router.get("/montecarlo/history", response_model=list[MonteCarloResponse])
async def risk_montecarlo_history(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> list[MonteCarloRun]:
    """G10 (docs/backlog.md): TODAS las runs del bot, mas recientes primero
    -- a diferencia de `/montecarlo`, que solo devuelve la ultima."""
    return list(
        (
            await session.execute(
                select(MonteCarloRun)
                .where(MonteCarloRun.bot_id == bot_id)
                .order_by(MonteCarloRun.ts.desc())
            )
        )
        .scalars()
        .all()
    )

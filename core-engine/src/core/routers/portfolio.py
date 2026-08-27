"""PARTE 9.2: `GET /api/v1/portfolio/blocks` + `/profiles` + `/correlations`
-- pestaña Portfolio (7.5). `block_target`/`profile_target`/
`profile_block_map` reflejan 1:1 `config/thresholds.seed.json` (10.3,
mismo patron de defaults-como-invocabilidad que `state_machines/types.py`,
G3, y `services/ums.py`, G5). `/correlations` lee las filas ya persistidas
por `correlations.py::run_correlation_job` (G5), no recalcula nada.

`GET /portfolio/benchmark` (G10, docs/backlog.md): "¿Añade valor real el
portfolio?" -- `services/benchmark.py` (nuevo)."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.config import get_settings
from core.db.base import get_session
from core.db.enums import PipelinePhase
from core.db.models.accounts import Bot
from core.db.models.governance import CorrelationMatrix
from core.services.benchmark import (
    compare_to_benchmark,
    load_sp500_monthly,
    portfolio_monthly_returns,
)

router = APIRouter(
    prefix="/api/v1/portfolio", tags=["portfolio"], dependencies=[Depends(get_current_user)]
)

_ACTIVE_PHASES = (PipelinePhase.F7, PipelinePhase.PRODUCCION)

BLOCK_TARGET: dict[str, float] = {"CONVEXO": 40.0, "CONCAVO": 40.0, "HIBRIDO": 20.0}
PROFILE_TARGET: dict[str, float] = {
    "TREND": 30.0,
    "MEAN_REVERSION": 25.0,
    "MOMENTUM": 15.0,
    "SMART_MONEY": 10.0,
    "GRID": 5.0,
    "SCALPING": 5.0,
    "AI_ML": 10.0,
}
PROFILE_BLOCK_MAP: dict[str, str] = {
    "TREND": "CONVEXO",
    "MOMENTUM": "CONVEXO",
    "MEAN_REVERSION": "CONCAVO",
    "GRID": "CONCAVO",
    "SCALPING": "CONCAVO",
    "SMART_MONEY": "HIBRIDO",
    "AI_ML": "HIBRIDO",
}


class AllocationRow(BaseModel):
    key: str
    target_pct: float
    real_pct: float
    delta_pct: float
    bot_count: int


class BenchmarkComparisonResponse(BaseModel):
    n_months: int
    cagr_portfolio: float
    cagr_benchmark: float
    alpha: float
    beta: float
    t_stat: float
    p_value: float
    information_ratio: float
    batting_average: float
    up_capture: float | None
    down_capture: float | None


class CorrelationRow(BaseModel):
    bot_a_id: int
    bot_b_id: int
    correlation: float
    is_redundant_pair: bool
    ts: datetime

    model_config = {"from_attributes": True}


async def _active_bot_allocations(session: AsyncSession) -> list[tuple[str, Decimal]]:
    rows = (
        await session.execute(
            select(Bot.profile, Bot.capital_allocated_pct).where(
                Bot.pipeline_phase.in_(_ACTIVE_PHASES)
            )
        )
    ).all()
    return [(profile.value, capital) for profile, capital in rows]


def _aggregate(
    keyed_allocations: list[tuple[str, Decimal]], targets: dict[str, float]
) -> list[AllocationRow]:
    total = sum((capital for _, capital in keyed_allocations), start=Decimal("0"))
    by_key: dict[str, tuple[Decimal, int]] = {}
    for key, capital in keyed_allocations:
        capital_sum, count = by_key.get(key, (Decimal("0"), 0))
        by_key[key] = (capital_sum + capital, count + 1)

    rows = []
    for key, target in targets.items():
        capital_sum, count = by_key.get(key, (Decimal("0"), 0))
        real_pct = float(capital_sum / total * 100) if total > 0 else 0.0
        rows.append(
            AllocationRow(
                key=key,
                target_pct=target,
                real_pct=real_pct,
                delta_pct=real_pct - target,
                bot_count=count,
            )
        )
    return rows


@router.get("/blocks", response_model=list[AllocationRow])
async def portfolio_blocks(session: AsyncSession = Depends(get_session)) -> list[AllocationRow]:
    allocations = await _active_bot_allocations(session)
    block_allocations = [(PROFILE_BLOCK_MAP[profile], capital) for profile, capital in allocations]
    return _aggregate(block_allocations, BLOCK_TARGET)


@router.get("/profiles", response_model=list[AllocationRow])
async def portfolio_profiles(session: AsyncSession = Depends(get_session)) -> list[AllocationRow]:
    allocations = await _active_bot_allocations(session)
    return _aggregate(allocations, PROFILE_TARGET)


@router.get("/benchmark", response_model=BenchmarkComparisonResponse | None)
async def portfolio_benchmark(
    session: AsyncSession = Depends(get_session),
) -> BenchmarkComparisonResponse | None:
    settings = get_settings()
    portfolio = await portfolio_monthly_returns(session, datetime.now(UTC))
    benchmark = load_sp500_monthly(settings.benchmark_csv_path)
    result = compare_to_benchmark(portfolio, benchmark)
    if result is None:
        return None
    return BenchmarkComparisonResponse.model_validate(result, from_attributes=True)


@router.get("/correlations", response_model=list[CorrelationRow])
async def portfolio_correlations(
    window_days: int | None = None, session: AsyncSession = Depends(get_session)
) -> list[CorrelationMatrix]:
    latest_query = select(func.max(CorrelationMatrix.ts))
    if window_days is not None:
        latest_query = latest_query.where(CorrelationMatrix.window_days == window_days)
    latest_ts = (await session.execute(latest_query)).scalar_one_or_none()
    if latest_ts is None:
        return []

    query = select(CorrelationMatrix).where(CorrelationMatrix.ts == latest_ts)
    if window_days is not None:
        query = query.where(CorrelationMatrix.window_days == window_days)
    return list((await session.execute(query)).scalars().all())

"""PARTE 9.2: `GET /api/v1/portfolio/blocks` + `/profiles` + `/correlations`
-- pestaña Portfolio (7.5). `block_target`/`profile_target`/
`profile_block_map` reflejan 1:1 `config/thresholds.seed.json` (10.3,
mismo patron de defaults-como-invocabilidad que `state_machines/types.py`,
G3, y `services/ums.py`, G5). `/correlations` lee las filas ya persistidas
por `correlations.py::run_correlation_job` (G5), no recalcula nada.

`GET /portfolio/benchmark` (G10, docs/backlog.md): "¿Añade valor real el
portfolio?" -- `services/benchmark.py` (nuevo)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.config import get_settings
from core.db.base import get_session
from core.db.enums import CorrelationSource, PipelinePhase
from core.db.models.accounts import Bot
from core.db.models.governance import CorrelationSnapshot, CorrelationSnapshotPair
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


class MonthlyReturnPointResponse(BaseModel):
    date: date
    portfolio_return: float
    benchmark_return: float


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
    monthly_points: list[MonthlyReturnPointResponse]


class CorrelationRow(BaseModel):
    bot_a_id: int
    bot_b_id: int
    correlation: float
    is_redundant_pair: bool
    snapshot_id: int
    source: CorrelationSource
    created_at: datetime


class CorrelationSnapshotResponse(BaseModel):
    id: int
    source: CorrelationSource
    status: str
    reason: str | None
    created_at: datetime
    window_start: datetime | None
    window_end: datetime | None
    window_days: int
    algorithm_version: str
    account_scope: dict[str, object]
    input_sha256: str
    pairs: list[CorrelationRow]


async def _active_bot_allocations(session: AsyncSession) -> list[tuple[str, Decimal]]:
    rows = (
        await session.execute(
            select(Bot.profile, Bot.capital_allocated_pct).where(
                Bot.pipeline_phase.in_(_ACTIVE_PHASES),
                Bot.profile.is_not(None),
                Bot.capital_allocated_pct.is_not(None),
            )
        )
    ).all()
    # `profile` y `capital_allocated_pct` son nullable y el tipo estatico no
    # refleja los `is_not(None)` de la consulta: se reafirman aqui en vez de
    # castear a ciegas.
    return [
        (profile.value, capital)
        for profile, capital in rows
        if profile is not None and capital is not None
    ]


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


@router.get("/correlations/latest", response_model=CorrelationSnapshotResponse | None)
async def latest_portfolio_correlation_snapshot(
    source: CorrelationSource = CorrelationSource.MT5_REAL,
    window_days: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> CorrelationSnapshotResponse | None:
    """Devuelve una sola evidencia con fuente explícita, nunca la legacy."""
    query = select(CorrelationSnapshot).where(CorrelationSnapshot.source == source)
    if window_days is not None:
        query = query.where(CorrelationSnapshot.window_days == window_days)
    snapshot = await session.scalar(query.order_by(CorrelationSnapshot.created_at.desc()).limit(1))
    if snapshot is None:
        return None
    pairs = list(
        (
            await session.scalars(
                select(CorrelationSnapshotPair)
                .where(CorrelationSnapshotPair.snapshot_id == snapshot.id)
                .order_by(CorrelationSnapshotPair.bot_a_id, CorrelationSnapshotPair.bot_b_id)
            )
        ).all()
    )
    return CorrelationSnapshotResponse(
        id=snapshot.id,
        source=snapshot.source,
        status=snapshot.status,
        reason=snapshot.reason,
        created_at=snapshot.created_at,
        window_start=snapshot.window_start,
        window_end=snapshot.window_end,
        window_days=snapshot.window_days,
        algorithm_version=snapshot.algorithm_version,
        account_scope=snapshot.account_scope,
        input_sha256=snapshot.input_sha256,
        pairs=[
            CorrelationRow(
                bot_a_id=pair.bot_a_id,
                bot_b_id=pair.bot_b_id,
                correlation=pair.correlation,
                is_redundant_pair=pair.is_redundant_pair,
                snapshot_id=snapshot.id,
                source=snapshot.source,
                created_at=snapshot.created_at,
            )
            for pair in pairs
        ],
    )


@router.get("/correlations", response_model=list[CorrelationRow])
async def portfolio_correlations(
    source: CorrelationSource = CorrelationSource.MT5_REAL,
    window_days: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[CorrelationRow]:
    """Compatibilidad de pares, limitada al último snapshot de una fuente."""
    snapshot = await latest_portfolio_correlation_snapshot(source, window_days, session)
    return [] if snapshot is None else snapshot.pairs

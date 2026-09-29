"""PARTE 9.2: `GET /api/v1/portfolio/blocks` + `/profiles` + `/correlations`
-- pestaña Portfolio (7.5). `block_target`/`profile_target`/
`profile_block_map` reflejan 1:1 `config/thresholds.seed.json` (10.3,
mismo patron de defaults-como-invocabilidad que `state_machines/types.py`,
G3, y `services/ums.py`, G5). `/correlations` lee las filas ya persistidas
por `correlations.py::run_correlation_job` (G5), no recalcula nada.

`GET /portfolio/benchmark` (G10, docs/backlog.md): "¿Añade valor real el
portfolio?" -- `services/benchmark.py` (nuevo)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.config import get_settings
from core.db.base import get_session
from core.db.enums import CorrelationSource, PipelinePhase
from core.db.models.accounts import Bot
from core.db.models.governance import CorrelationSnapshot, CorrelationSnapshotPair
from core.db.models.market import Trade
from core.routers.scope import AccountScope
from core.services.benchmark import (
    compare_to_benchmark,
    load_sp500_monthly,
    portfolio_monthly_returns,
)
from core.services.correlations import CorrelationServiceConfig

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
    n_obs: int | None
    low_confidence: bool


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


async def _active_bot_allocations(
    session: AsyncSession, account_id: int | None = None
) -> list[tuple[str, Decimal]]:
    query = select(Bot.profile, Bot.capital_allocated_pct).where(
        Bot.pipeline_phase.in_(_ACTIVE_PHASES),
        Bot.profile.is_not(None),
        Bot.capital_allocated_pct.is_not(None),
    )
    if account_id is not None:
        query = query.where(Bot.account_id == account_id)
    rows = (await session.execute(query)).all()
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
async def portfolio_blocks(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> list[AllocationRow]:
    allocations = await _active_bot_allocations(session, account_id)
    block_allocations = [(PROFILE_BLOCK_MAP[profile], capital) for profile, capital in allocations]
    return _aggregate(block_allocations, BLOCK_TARGET)


@router.get("/profiles", response_model=list[AllocationRow])
async def portfolio_profiles(
    account_id: AccountScope, session: AsyncSession = Depends(get_session)
) -> list[AllocationRow]:
    allocations = await _active_bot_allocations(session, account_id)
    return _aggregate(allocations, PROFILE_TARGET)


@router.get("/benchmark", response_model=BenchmarkComparisonResponse | None)
async def portfolio_benchmark(
    account_id: AccountScope,
    session: AsyncSession = Depends(get_session),
) -> BenchmarkComparisonResponse | None:
    settings = get_settings()
    portfolio = await portfolio_monthly_returns(session, datetime.now(UTC), account_id)
    benchmark = load_sp500_monthly(settings.benchmark_csv_path)
    result = compare_to_benchmark(portfolio, benchmark)
    if result is None:
        return None
    return BenchmarkComparisonResponse.model_validate(result, from_attributes=True)


@router.get("/correlations/latest", response_model=CorrelationSnapshotResponse | None)
async def latest_portfolio_correlation_snapshot(
    account_id: AccountScope,
    source: CorrelationSource = CorrelationSource.MT5_REAL,
    window_days: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> CorrelationSnapshotResponse | None:
    """Devuelve una sola evidencia con fuente explícita, nunca la legacy. Con
    `account_id` (ADR 0013) solo cuentan los snapshots calculados para esa cuenta."""
    low_confidence_obs = CorrelationServiceConfig().low_confidence_obs
    query = select(CorrelationSnapshot).where(CorrelationSnapshot.source == source)
    if window_days is not None:
        query = query.where(CorrelationSnapshot.window_days == window_days)
    if account_id is not None:
        query = query.where(
            CorrelationSnapshot.account_scope["account_id"].as_integer() == account_id
        )
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
                n_obs=pair.n_obs,
                low_confidence=pair.n_obs is not None and pair.n_obs < low_confidence_obs,
            )
            for pair in pairs
        ],
    )


@router.get("/correlations", response_model=list[CorrelationRow])
async def portfolio_correlations(
    account_id: AccountScope,
    source: CorrelationSource = CorrelationSource.MT5_REAL,
    window_days: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[CorrelationRow]:
    """Compatibilidad de pares, limitada al último snapshot de una fuente."""
    snapshot = await latest_portfolio_correlation_snapshot(account_id, source, window_days, session)
    return [] if snapshot is None else snapshot.pairs


class BotCoverageRow(BaseModel):
    bot_id: int
    name: str
    included: bool
    days: int | None
    trades: int | None
    reason: str | None


_REASON_NO_SNAPSHOT = "SIN_SNAPSHOT"
_REASON_INSUFFICIENT = "HISTORIA_INSUFICIENTE"
_REASON_NO_PAIRS = "SIN_PARES_VALIDOS"
_REASON_NO_BACKTEST = "SIN_EVIDENCIA_BACKTEST"


@router.get("/correlations/coverage", response_model=list[BotCoverageRow])
async def correlation_coverage(
    account_id: AccountScope,
    source: CorrelationSource = CorrelationSource.MT5_REAL,
    session: AsyncSession = Depends(get_session),
) -> list[BotCoverageRow]:
    """Bots instalados en la cuenta y si entran en su ultima matriz, con el
    motivo cuando no (ADR 0013). Sin cuenta no hay universo definido: lista vacia."""
    if account_id is None:
        return []
    config = CorrelationServiceConfig()
    bots = (
        await session.execute(
            select(Bot.id, Bot.name)
            .where(Bot.account_id == account_id, Bot.pipeline_phase != PipelinePhase.CEMENTERIO)
            .order_by(Bot.id)
        )
    ).all()
    snapshot = await session.scalar(
        select(CorrelationSnapshot)
        .where(
            CorrelationSnapshot.source == source,
            CorrelationSnapshot.account_scope["account_id"].as_integer() == account_id,
        )
        .order_by(CorrelationSnapshot.created_at.desc())
        .limit(1)
    )
    in_pairs: set[int] = set()
    if snapshot is not None:
        pair_rows = (
            await session.execute(
                select(CorrelationSnapshotPair.bot_a_id, CorrelationSnapshotPair.bot_b_id).where(
                    CorrelationSnapshotPair.snapshot_id == snapshot.id
                )
            )
        ).all()
        for bot_a_id, bot_b_id in pair_rows:
            in_pairs.update((bot_a_id, bot_b_id))

    activity: dict[int, tuple[int, int]] = {}
    if source == CorrelationSource.MT5_REAL:
        window_start = datetime.now(UTC) - timedelta(days=config.window_days)
        rows = (
            await session.execute(
                select(
                    Trade.bot_id,
                    func.count(func.distinct(func.date(Trade.close_time))),
                    func.count(Trade.id),
                )
                .where(
                    Trade.account_id == account_id,
                    Trade.bot_id.is_not(None),
                    Trade.close_time.is_not(None),
                    Trade.close_time >= window_start,
                )
                .group_by(Trade.bot_id)
            )
        ).all()
        activity = {bot_id: (days, trades) for bot_id, days, trades in rows if bot_id is not None}

    result: list[BotCoverageRow] = []
    for bot_id, name in bots:
        included = bot_id in in_pairs
        days, trades = (
            activity.get(bot_id, (0, 0)) if source == CorrelationSource.MT5_REAL else (None, None)
        )
        reason: str | None = None
        if not included:
            if source == CorrelationSource.MT5_BACKTEST:
                reason = _REASON_NO_BACKTEST
            elif snapshot is None:
                reason = _REASON_NO_SNAPSHOT
            elif (days or 0) < config.min_days_for_correlation and (
                trades or 0
            ) < config.min_trades_for_correlation:
                reason = _REASON_INSUFFICIENT
            else:
                reason = _REASON_NO_PAIRS
        result.append(
            BotCoverageRow(
                bot_id=bot_id, name=name, included=included, days=days, trades=trades, reason=reason
            )
        )
    return result
